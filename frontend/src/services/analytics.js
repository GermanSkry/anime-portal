import * as Sentry from '@sentry/react'
import posthog from 'posthog-js'

// Both keys are public by design: they ship inside the bundle either way.
// Left empty, each SDK simply never starts, so a clone works with no setup.
const POSTHOG_KEY = import.meta.env.VITE_POSTHOG_KEY || ''
const POSTHOG_HOST = import.meta.env.VITE_POSTHOG_HOST || 'https://eu.i.posthog.com'
const SENTRY_DSN = import.meta.env.VITE_SENTRY_DSN || ''
const ENVIRONMENT = import.meta.env.MODE

let posthogReady = false

export function initAnalytics() {
  if (SENTRY_DSN) {
    Sentry.init({
      dsn: SENTRY_DSN,
      environment: ENVIRONMENT,
      // 10%: enough signal for a portfolio, well inside the free quota
      tracesSampleRate: 0.1,
    })
  }

  if (POSTHOG_KEY) {
    posthog.init(POSTHOG_KEY, {
      api_host: POSTHOG_HOST,
      capture_pageview: true,
      disable_surveys: true, // not used, and it pulls another script on every load
      persistence: 'localStorage+cookie',
      // PostHog drops events from bot-looking user agents, and a headless browser
      // is one. Off by default; the e2e check sets it so the events can be verified.
      opt_out_useragent_filter: import.meta.env.VITE_POSTHOG_ALLOW_BOTS === 'true',
    })
    // stamp every browser event, so a local run can be filtered out of the real numbers
    posthog.register({ environment: ENVIRONMENT })
    posthogReady = true
  }
}

/** PostHog's anonymous visitor id, sent to our APIs so their events join these. */
export function clientId() {
  try {
    return posthogReady ? posthog.get_distinct_id() : ''
  } catch {
    return ''
  }
}

/** Fire-and-forget product event. Never throws: analytics must not break the UI. */
export function track(event, properties = {}) {
  if (!posthogReady) return
  try {
    posthog.capture(event, properties)
  } catch (error) {
    console.warn('analytics:', error)
  }
}
