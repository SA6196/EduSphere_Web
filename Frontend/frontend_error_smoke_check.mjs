import { normalizeApiError, safeServerMessage, errorPresentation, isQuizAttemptRequired } from './src/utils/errors.js'

const raw = `('HY000', '[HY000] [Oracle][ODBC][Ora]ORA-20113: Maximum quiz attempts have been used.\\nORA-06512: at "EDUSPHERE_OWNER.PR_START_QUIZ_ATTEMPT", line 54\\nORA-06512: at line 5 (20113) (SQLExecDirectW)')`
const n = normalizeApiError({ body: { message: raw, error_code: 'DatabaseError' }, status: 400 })
if (n.message !== 'You have used all attempts allowed for this quiz.') throw new Error(`Unexpected sanitized message: ${n.message}`)
if (n.oracleCode !== '20113') throw new Error(`Expected ORA-20113, got ${n.oracleCode}`)
if (/ODBC|EDUSPHERE_OWNER|SQLExec|ORA-06512/i.test(n.message)) throw new Error('Technical details leaked into user message')

const p = errorPresentation({ ...new Error(n.message), status: 400, serverMessage: raw, oracleCode: n.oracleCode }, 'quiz')
if (p.title !== 'No quiz attempts remaining') throw new Error(`Unexpected presentation title: ${p.title}`)
if (p.retryable) throw new Error('Business-rule error should not be retryable')

if (!isQuizAttemptRequired({ serverMessage: 'Start the quiz attempt before loading quiz content.' })) throw new Error('Quiz attempt gate was not recognized')
if (isQuizAttemptRequired({ serverMessage: 'Maximum quiz attempts have been used.' })) throw new Error('Max-attempt error must not be mistaken for attempt-required')

const html = '<!doctype html><html><body>Traceback Django Version Request Method</body></html>'
const safe = safeServerMessage(html, 500)
if (safe.includes('<html>') || safe.includes('Traceback')) throw new Error('HTML/debug details leaked')

console.log('FRONTEND ERROR-HANDLING SMOKE CHECK: PASS')
