<template>
  <div class="aurora" aria-hidden="true">
    <canvas v-if="webglOk" ref="canvas" class="aurora__canvas" />
    <div v-else class="aurora__fallback" :style="fallbackStyle" />
    <div class="aurora__grain" />
    <div class="aurora__vignette" />
  </div>
</template>

<script setup lang="ts">
/**
 * Full-bleed WebGL aurora. Zero dependencies — one quad, one fragment shader.
 *
 * The hue tweens toward the focused module's accent (see useAmbience), the
 * field drifts with pointer / right-stick parallax, and detail pages dim it.
 * Falls back to a static CSS gradient when WebGL is unavailable, and renders
 * a single still frame when the user prefers reduced motion.
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { hexToRgb01, setParallax, useAmbience } from '../../composables/useAmbience'

const ambience = useAmbience()
const canvas = ref<HTMLCanvasElement | null>(null)
const webglOk = ref(true)

const fallbackStyle = computed(() => ({
  background: `radial-gradient(120% 90% at 20% 0%, ${ambience.accent}26, transparent 55%),` +
    `radial-gradient(110% 80% at 85% 15%, ${ambience.accent2}21, transparent 60%),` +
    'linear-gradient(160deg, #04060d 0%, #070b16 55%, #04060d 100%)',
}))

const VERT = `
attribute vec2 a_pos;
void main() { gl_Position = vec4(a_pos, 0.0, 1.0); }
`

const FRAG = `
precision highp float;
uniform vec2  u_res;
uniform float u_time;
uniform vec3  u_colorA;
uniform vec3  u_colorB;
uniform vec2  u_par;
uniform float u_dim;

float hash(vec2 p) {
  return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);
}
float noise(vec2 p) {
  vec2 i = floor(p);
  vec2 f = fract(p);
  vec2 u = f * f * (3.0 - 2.0 * f);
  return mix(mix(hash(i), hash(i + vec2(1.0, 0.0)), u.x),
             mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
}
float fbm(vec2 p) {
  float v = 0.0;
  float a = 0.55;
  mat2 rot = mat2(0.8, 0.6, -0.6, 0.8);
  for (int i = 0; i < 5; i++) {
    v += a * noise(p);
    p = rot * p * 2.03;
    a *= 0.5;
  }
  return v;
}

void main() {
  vec2 uv = gl_FragCoord.xy / u_res.xy;
  vec2 p = uv;
  p.x *= u_res.x / u_res.y;
  p += u_par * 0.06;

  float t = u_time * 0.035;

  // Two slow counter-flowing aurora bands.
  float bandA = fbm(vec2(p.x * 1.4 + t, p.y * 2.2 - t * 0.6));
  float bandB = fbm(vec2(p.x * 0.9 - t * 0.8, p.y * 1.6 + t * 0.4) + 3.7);

  float curtainA = smoothstep(0.35, 0.95, bandA) * (1.0 - smoothstep(0.0, 1.15, abs(uv.y - 0.72 - 0.18 * sin(p.x * 1.3 + t * 2.0))));
  float curtainB = smoothstep(0.40, 0.95, bandB) * (1.0 - smoothstep(0.0, 1.05, abs(uv.y - 0.30 + 0.15 * cos(p.x * 1.1 - t * 1.6))));

  vec3 base = mix(vec3(0.012, 0.020, 0.045), vec3(0.020, 0.030, 0.066), uv.y);
  vec3 col = base;
  col += u_colorA * curtainA * 0.36;
  col += u_colorB * curtainB * 0.26;

  // Soft horizon glow at the carousel line.
  float glow = exp(-abs(uv.y - 0.30) * 5.0);
  col += mix(u_colorA, u_colorB, uv.x) * glow * 0.05;

  // Sparse star field.
  vec2 g = floor(gl_FragCoord.xy / 2.0);
  float star = step(0.9985, hash(g)) * (0.4 + 0.6 * sin(u_time * 0.8 + hash(g.yx) * 6.28));
  col += vec3(star) * 0.35 * (1.0 - uv.y * 0.6);

  col *= 1.0 - u_dim * 0.62;
  gl_FragColor = vec4(col, 1.0);
}
`

let gl: WebGLRenderingContext | null = null
let program: WebGLProgram | null = null
let raf = 0
let start = 0
let reducedMotion = false
let resizeObserver: ResizeObserver | null = null

// Tweened uniforms
const cur = { a: hexToRgb01('#7DD3FC'), b: hexToRgb01('#A78BFA'), px: 0, py: 0, dim: 0 }

function compile(glx: WebGLRenderingContext, type: number, src: string) {
  const shader = glx.createShader(type)
  if (!shader) return null
  glx.shaderSource(shader, src)
  glx.compileShader(shader)
  if (!glx.getShaderParameter(shader, glx.COMPILE_STATUS)) {
    console.warn('[aurora]', glx.getShaderInfoLog(shader))
    glx.deleteShader(shader)
    return null
  }
  return shader
}

function setup(): boolean {
  const el = canvas.value
  if (!el) return false
  gl = el.getContext('webgl', { antialias: false, alpha: false, powerPreference: 'low-power' })
  if (!gl) return false

  const vs = compile(gl, gl.VERTEX_SHADER, VERT)
  const fs = compile(gl, gl.FRAGMENT_SHADER, FRAG)
  if (!vs || !fs) return false

  program = gl.createProgram()
  if (!program) return false
  gl.attachShader(program, vs)
  gl.attachShader(program, fs)
  gl.linkProgram(program)
  if (!gl.getProgramParameter(program, gl.LINK_STATUS)) return false
  gl.useProgram(program)

  const quad = gl.createBuffer()
  gl.bindBuffer(gl.ARRAY_BUFFER, quad)
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 3, -1, -1, 3]), gl.STATIC_DRAW)
  const loc = gl.getAttribLocation(program, 'a_pos')
  gl.enableVertexAttribArray(loc)
  gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0)
  return true
}

function resize() {
  const el = canvas.value
  if (!el || !gl) return
  const dpr = Math.min(window.devicePixelRatio || 1, 1.5) // cap for perf on 4K/TV
  const w = Math.floor(el.clientWidth * dpr)
  const h = Math.floor(el.clientHeight * dpr)
  if (el.width !== w || el.height !== h) {
    el.width = w
    el.height = h
    gl.viewport(0, 0, w, h)
  }
}

const lerp = (a: number, b: number, t: number) => a + (b - a) * t

function frame(now: number) {
  if (!gl || !program) return
  if (!start) start = now
  resize()

  const ta = hexToRgb01(ambience.accent)
  const tb = hexToRgb01(ambience.accent2)
  const k = 0.045 // tween speed toward the focused module's hue
  for (let i = 0; i < 3; i++) {
    cur.a[i] = lerp(cur.a[i], ta[i], k)
    cur.b[i] = lerp(cur.b[i], tb[i], k)
  }
  cur.px = lerp(cur.px, ambience.parallaxX, 0.06)
  cur.py = lerp(cur.py, ambience.parallaxY, 0.06)
  cur.dim = lerp(cur.dim, ambience.dim, 0.08)

  const u = (name: string) => gl!.getUniformLocation(program!, name)
  gl.uniform2f(u('u_res'), canvas.value!.width, canvas.value!.height)
  gl.uniform1f(u('u_time'), (now - start) / 1000)
  gl.uniform3f(u('u_colorA'), cur.a[0], cur.a[1], cur.a[2])
  gl.uniform3f(u('u_colorB'), cur.b[0], cur.b[1], cur.b[2])
  gl.uniform2f(u('u_par'), cur.px, -cur.py)
  gl.uniform1f(u('u_dim'), cur.dim)
  gl.drawArrays(gl.TRIANGLES, 0, 3)

  if (!reducedMotion) raf = requestAnimationFrame(frame)
}

function onPointerMove(event: PointerEvent) {
  const x = (event.clientX / window.innerWidth) * 2 - 1
  const y = (event.clientY / window.innerHeight) * 2 - 1
  setParallax(x * 0.5, y * 0.5)
}

function onContextLost(event: Event) {
  event.preventDefault()
  cancelAnimationFrame(raf)
}
function onContextRestored() {
  if (setup()) raf = requestAnimationFrame(frame)
}

onMounted(() => {
  reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  if (!setup()) {
    webglOk.value = false
    return
  }
  canvas.value?.addEventListener('webglcontextlost', onContextLost)
  canvas.value?.addEventListener('webglcontextrestored', onContextRestored)
  window.addEventListener('pointermove', onPointerMove, { passive: true })
  resizeObserver = new ResizeObserver(() => resize())
  if (canvas.value) resizeObserver.observe(canvas.value)
  raf = requestAnimationFrame(frame)
})

onBeforeUnmount(() => {
  cancelAnimationFrame(raf)
  window.removeEventListener('pointermove', onPointerMove)
  canvas.value?.removeEventListener('webglcontextlost', onContextLost)
  canvas.value?.removeEventListener('webglcontextrestored', onContextRestored)
  resizeObserver?.disconnect()
  gl = null
  program = null
})
</script>

<style lang="scss" scoped>
.aurora {
  position: fixed;
  inset: 0;
  z-index: 0;
  background: #04060d;
}
.aurora__canvas,
.aurora__fallback {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  display: block;
}
.aurora__grain {
  position: absolute;
  inset: 0;
  opacity: 0.05;
  pointer-events: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='2'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='0.6'/%3E%3C/svg%3E");
}
.aurora__vignette {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: radial-gradient(120% 100% at 50% 40%, transparent 55%, rgba(2, 4, 9, 0.65) 100%);
}
</style>
