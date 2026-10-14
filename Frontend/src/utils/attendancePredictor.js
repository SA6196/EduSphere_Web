/** Student-side attendance planning helpers. Read-only and policy-explicit.
 * A percentage is UNDEFINED until at least one session counts under the
 * selected institutional status policy. Unrecorded and upcoming sessions
 * never enter the observed denominator.
 */
export const ATTENDANCE_STATUSES = ['PRESENT', 'ABSENT', 'LATE', 'EXCUSED']

export function clampInteger(value, minimum, maximum) {
  const number = Number(value)
  return Number.isFinite(number) ? Math.max(minimum, Math.min(maximum, Math.trunc(number))) : minimum
}

export function makeStatusCounts(sessions = []) {
  const counts = { PRESENT: 0, ABSENT: 0, LATE: 0, EXCUSED: 0, unrecorded: 0, upcoming: 0 }
  for (const session of sessions) {
    const status = String(session.attendance_status || '').toUpperCase()
    if (ATTENDANCE_STATUSES.includes(status)) counts[status] += 1
    else if (session.session_timing === 'UPCOMING') counts.upcoming += 1
    else counts.unrecorded += 1
  }
  return counts
}

/** Policy values for LATE/EXCUSED: present, absent, exclude. */
export function scoreAttendance(counts, latePolicy = 'exclude', excusedPolicy = 'exclude') {
  const valid = new Set(['present', 'absent', 'exclude'])
  const policy = [latePolicy, excusedPolicy].map(value => valid.has(value) ? value : 'exclude')
  let attended = Number(counts.PRESENT || 0)
  let eligible = attended + Number(counts.ABSENT || 0)
  for (const [index, status] of ['LATE', 'EXCUSED'].entries()) {
    const n = Number(counts[status] || 0)
    if (policy[index] !== 'exclude') eligible += n
    if (policy[index] === 'present') attended += n
  }
  return { attended, eligible, percentage: eligible > 0 ? attended / eligible * 100 : null }
}

export function predictAttendance(attended, eligible, futureClasses, futureMissed, targetPercent) {
  const a = Math.max(0, Number(attended) || 0)
  const e = Math.max(a, Number(eligible) || 0)
  const future = clampInteger(futureClasses, 0, 120)
  const missed = clampInteger(futureMissed, 0, future)
  const target = clampInteger(targetPercent, 1, 100)
  const t = target / 100
  const current = e ? 100 * a / e : null
  const predicted = e + future ? 100 * (a + future - missed) / (e + future) : null
  const best = e + future ? 100 * (a + future) / (e + future) : null
  const worst = e + future ? 100 * a / (e + future) : null
  let needToAttend = null
  let mayMiss = null
  if (e > 0) {
    // Null means impossible in any finite number of perfect future classes.
    needToAttend = current + 1e-9 >= target ? 0 : t === 1 ? null : Math.max(0, Math.ceil((t * e - a) / (1 - t) - 1e-9))
    // Only meaningful when target is already met; null means not safe to skip.
    mayMiss = current + 1e-9 >= target ? Math.max(0, Math.floor(a / t - e + 1e-9)) : null
  }
  return { current, predicted, best, worst, future, missed, target, needToAttend, mayMiss }
}

export function buildProjectionPoints(attended, eligible, future, missed) {
  const count = clampInteger(future, 0, 120)
  const misses = clampInteger(missed, 0, count)
  if (!(eligible > 0)) return []
  return Array.from({ length: count + 1 }, (_, i) => {
    // Missed sessions are spread approximately evenly for intermediate points;
    // endpoint is exact and independent of when the missed sessions occur.
    const missedAtI = count ? Math.round(i * misses / count) : 0
    const denom = eligible + i
    return {
      step: i,
      best: 100 * (attended + i) / denom,
      plan: 100 * (attended + i - missedAtI) / denom,
      worst: 100 * attended / denom,
    }
  })
}
