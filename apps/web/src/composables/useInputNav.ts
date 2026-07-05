/**
 * Console-style input for the Big Picture shell.
 *
 * Unifies keyboard arrows and the Gamepad API (d-pad + left stick) into a
 * single event stream: 'left' | 'right' | 'up' | 'down' | 'confirm' | 'back' | 'menu'.
 *
 * - Keyboard: arrows / Enter / Escape / Ctrl-or-Cmd+K (menu = command palette)
 * - Gamepad:  d-pad & left stick / A (0) confirm / B (1) back / Start (9) menu
 * - Stick and held d-pad auto-repeat with an initial delay, like a console UI.
 */
import { onBeforeUnmount, onMounted } from 'vue'
import { setParallax } from './useAmbience'

export type NavAction = 'left' | 'right' | 'up' | 'down' | 'confirm' | 'back' | 'menu'
export type NavHandler = (action: NavAction, source: 'keyboard' | 'gamepad') => void

const REPEAT_DELAY = 380 // ms before auto-repeat kicks in
const REPEAT_RATE = 130 // ms between repeats
const STICK_DEADZONE = 0.35

interface RepeatState {
  action: NavAction | null
  since: number
  lastFire: number
}

export function useInputNav(handler: NavHandler, options: { capture?: boolean } = {}) {
  let raf = 0
  let polling = false
  const repeat: RepeatState = { action: null, since: 0, lastFire: 0 }
  const pressed = new Set<string>()

  function onKeydown(event: KeyboardEvent) {
    const target = event.target as HTMLElement | null
    const typing = !!target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable)

    if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
      event.preventDefault()
      handler('menu', 'keyboard')
      return
    }
    if (typing) return

    const map: Record<string, NavAction> = {
      ArrowLeft: 'left',
      ArrowRight: 'right',
      ArrowUp: 'up',
      ArrowDown: 'down',
      Enter: 'confirm',
      ' ': 'confirm',
      Escape: 'back',
      Backspace: 'back',
    }
    const action = map[event.key]
    if (!action) return
    event.preventDefault()
    handler(action, 'keyboard')
  }

  function fire(action: NavAction, now: number) {
    handler(action, 'gamepad')
    repeat.action = action
    repeat.since = now
    repeat.lastFire = now
  }

  function pollGamepads(now: number) {
    const pads = navigator.getGamepads ? navigator.getGamepads() : []
    let dir: NavAction | null = null
    let confirm = false
    let back = false
    let menu = false
    let px = 0
    let py = 0

    for (const pad of pads) {
      if (!pad || !pad.connected) continue
      const [lx = 0, ly = 0, rx = 0, ry = 0] = pad.axes
      // Right stick (or left, scaled down) drifts the aurora.
      px = Math.abs(rx) > 0.08 ? rx : lx * 0.4
      py = Math.abs(ry) > 0.08 ? ry : ly * 0.4

      const b = (i: number) => !!pad.buttons[i]?.pressed
      if (b(14) || lx < -STICK_DEADZONE) dir = 'left'
      else if (b(15) || lx > STICK_DEADZONE) dir = 'right'
      else if (b(12) || ly < -STICK_DEADZONE) dir = 'up'
      else if (b(13) || ly > STICK_DEADZONE) dir = 'down'
      if (b(0)) confirm = true
      if (b(1)) back = true
      if (b(9)) menu = true
      if (dir || confirm || back || menu) break
    }

    setParallax(px, py)

    // Edge-trigger buttons; auto-repeat directions.
    for (const [key, active] of [
      ['confirm', confirm],
      ['back', back],
      ['menu', menu],
    ] as const) {
      if (active && !pressed.has(key)) {
        pressed.add(key)
        handler(key, 'gamepad')
      } else if (!active) {
        pressed.delete(key)
      }
    }

    if (dir) {
      if (repeat.action !== dir) {
        fire(dir, now)
      } else if (now - repeat.since > REPEAT_DELAY && now - repeat.lastFire > REPEAT_RATE) {
        handler(dir, 'gamepad')
        repeat.lastFire = now
      }
    } else {
      repeat.action = null
    }
  }

  function loop(now: number) {
    if (!polling) return
    pollGamepads(now)
    raf = requestAnimationFrame(loop)
  }

  function startPolling() {
    if (polling) return
    polling = true
    raf = requestAnimationFrame(loop)
  }

  function stopPolling() {
    polling = false
    cancelAnimationFrame(raf)
  }

  function onGamepadConnected() {
    startPolling()
  }
  function onGamepadDisconnected() {
    const pads = navigator.getGamepads ? navigator.getGamepads() : []
    if (![...pads].some((p) => p && p.connected)) stopPolling()
  }

  onMounted(() => {
    window.addEventListener('keydown', onKeydown, { capture: options.capture ?? false })
    window.addEventListener('gamepadconnected', onGamepadConnected)
    window.addEventListener('gamepaddisconnected', onGamepadDisconnected)
    const pads = navigator.getGamepads ? navigator.getGamepads() : []
    if ([...pads].some((p) => p && p.connected)) startPolling()
  })

  onBeforeUnmount(() => {
    window.removeEventListener('keydown', onKeydown, { capture: options.capture ?? false } as EventListenerOptions)
    window.removeEventListener('gamepadconnected', onGamepadConnected)
    window.removeEventListener('gamepaddisconnected', onGamepadDisconnected)
    stopPolling()
  })
}
