-- Phase C: capture inbox triage state.
-- CaptureItems get an explicit lifecycle so the inbox can be triaged
-- (keyboard j/k/t/n/a in the web shell) instead of growing forever.
-- status: inbox | triaged | archived

ALTER TABLE capture_items ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'inbox';
ALTER TABLE capture_items ADD COLUMN IF NOT EXISTS triaged_note_id UUID;
CREATE INDEX IF NOT EXISTS idx_capture_items_status ON capture_items (status, created_at DESC);
