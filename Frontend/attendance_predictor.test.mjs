import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { ATTENDANCE_STATUSES, makeStatusCounts, scoreAttendance, predictAttendance, buildProjectionPoints, clampInteger } from './src/utils/attendancePredictor.js'

const seen = [{ attendance_status: 'PRESENT' }, { attendance_status: 'PRESENT' },
  { attendance_status: 'ABSENT' }, { attendance_status: 'LATE' },
  { attendance_status: 'EXCUSED' }, { attendance_status: null, session_timing: 'UPCOMING' },
  { attendance_status: null, session_timing: 'PAST_OR_TODAY' }]

test('all four statuses match the Oracle check constraint', () => assert.deepEqual(ATTENDANCE_STATUSES, ['PRESENT','ABSENT','LATE','EXCUSED']))
test('unrecorded and upcoming sessions never count as absent', () => {
  assert.deepEqual(makeStatusCounts(seen), { PRESENT: 2, ABSENT: 1, LATE: 1, EXCUSED: 1, unrecorded: 1, upcoming: 1 })
})
test('default status policy excludes late and excused', () => {
  const actual = scoreAttendance(makeStatusCounts(seen))
  assert.equal(actual.attended, 2)
  assert.equal(actual.eligible, 3)
  assert.ok(Math.abs(actual.percentage - 200 / 3) < 1e-9)
})
test('late and excused policy can count as present or absent separately', () => {
  const scores = scoreAttendance(makeStatusCounts(seen), 'present', 'absent')
  assert.equal(scores.attended, 3)
  assert.equal(scores.eligible, 5)
  assert.equal(scores.percentage, 60)
})
test('invalid policies default to exclude', () => assert.equal(scoreAttendance(makeStatusCounts(seen),'nonsense','bad').eligible,3))
test('zero eligible sessions means undefined observed percentage', () => assert.equal(scoreAttendance(makeStatusCounts([{session_timing:'UPCOMING'}])).percentage,null))
test('number of needed attended sessions satisfies exact target', () => {
  const plan = predictAttendance(7,10,2,0,75)
  assert.equal(plan.current, 70)
  assert.equal(plan.predicted, 75)
  assert.equal(plan.needToAttend, 2)
  assert.equal(plan.mayMiss, null)
})
test('safe misses are computed from current >= target', () => {
  const plan = predictAttendance(9,10,4,1,75)
  assert.equal(plan.mayMiss, 2)
  assert.equal(plan.needToAttend, 0)
  assert.equal(plan.predicted, 12/14 * 100)
})
test('cannot reach a perfect 100 percent once a counted absence exists', () => {
  const plan = predictAttendance(9,10,10,0,100)
  assert.equal(plan.needToAttend, null)
  assert.equal(plan.mayMiss, null)
})
test('perfect score has no miss budget at target 100', () => assert.equal(predictAttendance(10,10,1,0,100).mayMiss,0))
test('invalid and out-of-range future classes and misses clamp safely', () => {
  assert.equal(clampInteger('xxx',0,20),0)
  const plan = predictAttendance(8,10,130,150,75)
  assert.equal(plan.future,120)
  assert.equal(plan.missed,120)
  assert.equal(plan.predicted, 8/130 * 100)
})
test('planned line endpoint equals the exact what-if projection', () => {
  const plan = predictAttendance(17,23,9,3,75)
  const points = buildProjectionPoints(17,23,9,3)
  assert.equal(points.length,10)
  assert.ok(Math.abs(points[0].plan - 17/23*100) < 1e-9)
  assert.ok(Math.abs(points.at(-1).plan - plan.predicted) < 1e-9)
  assert.equal(points.at(-1).best,plan.best)
  assert.equal(points.at(-1).worst,plan.worst)
})
test('the chart handles no observed records or no future sessions', () => {
  assert.deepEqual(buildProjectionPoints(0,0,12,2),[])
  assert.equal(buildProjectionPoints(3,4,0,0).length,1)
})
test('percentage never counts unknown future sessions in the denominator', () => {
  const counts = makeStatusCounts([{attendance_status:'PRESENT'},{session_timing:'UPCOMING'},{session_timing:'PAST_OR_TODAY'}])
  assert.equal(scoreAttendance(counts).percentage,100)
})
test('the attendance page has the new chart component but performance stays graph-free', () => {
  const attendance = readFileSync(new URL('./src/views/student/StudentAttendanceView.vue',import.meta.url),'utf8')
  const performance = readFileSync(new URL('./src/views/student/StudentPerformanceView.vue',import.meta.url),'utf8')
  assert.match(attendance,/AttendanceAnalytics/)
  assert.match(attendance,/:sessions="semesterSessions"/)
  assert.doesNotMatch(performance,/AttendanceAnalytics/)
})
test('the predictor calls no backend endpoint and does not write data', () => {
  const component = readFileSync(new URL('./src/components/AttendanceAnalytics.vue',import.meta.url),'utf8')
  assert.doesNotMatch(component, /(?:fetch\(|axios\.|api\.|\bPOST\b|\bPATCH\b|\bDELETE\b)/)
  assert.match(component, /projection/i)
  assert.match(component, /official Oracle rule/)
  assert.match(component, /hypothetical predictor/)
})
