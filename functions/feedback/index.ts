/**
 * Supabase Edge Function: the one-tap feedback endpoint (PRD FR-4).
 *
 * STUB — implemented in Milestone M4 (~60 lines, docs/02 §2).
 *
 * Design decided now:
 * - GET /feedback?item=<id>&verdict=<useful|not_relevant|knew_it|deep_dive>&sig=<hmac>
 * - Verifies the HMAC signature (FEEDBACK_HMAC_SECRET) before writing anything;
 *   a bad signature returns 403 and writes nothing.
 * - On success: inserts one feedback row, returns a plain
 *   "Recorded — you can close this tab" page. No login, no cookies, no tracking.
 * - This is the ONLY server-side web surface in V1 (PRD §7.1).
 */

// TODO(M4): Deno.serve handler per the docblock above.
