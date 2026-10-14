const ORACLE_MESSAGES = {
  '20010': 'Attendance cannot be recorded because the student is not enrolled in this class.',
  '20016': 'You are not actively enrolled in the class for this quiz.',
  '20017': 'You have used all attempts allowed for this quiz.',
  '20018': 'This question does not belong to the current quiz attempt.',
  '20019': 'The selected option does not belong to this question.',
  '20020': 'The selected assessment and enrollment belong to different classes.',
  '20021': 'The entered mark is higher than the maximum marks for this assessment.',
  '20022': 'You are not assigned to this class.',
  '20023': 'Only an assigned instructor or administrator can record marks.',
  '20110': 'This quiz has not opened yet.',
  '20111': 'This quiz is already closed.',
  '20112': 'You are not enrolled in the class for this quiz.',
  '20113': 'You have used all attempts allowed for this quiz.',
  '20202': 'Enrollment is available only while the class is open.',
  '20203': 'This class has reached its enrollment capacity.',
  '20209': 'Marks can be recorded only for an active or completed enrollment.',
  '20305': 'Only an active student can be enrolled.',
  '20306': 'The student account must be active before enrollment.',
  '20307': 'The enrollment date is outside the allowed semester period.',
  '20311': 'This quiz has not opened yet.',
  '20312': 'This quiz is already closed.',
  '20313': 'The student account must be active to attempt this quiz.',
  '20330': 'The account recording this mark must be active.',
  '20404': 'You already have an open attempt for this quiz. Reopen the quiz instead of starting another attempt.',
  '20407': 'The time limit for this quiz attempt has expired.',
  '20408': 'The quiz closing time has passed, so this attempt can no longer be changed or submitted.',
  '20409': 'Answers can no longer be changed because this quiz attempt has already been submitted.',
  '20411': 'You are not authorized to record attendance for this class.',
  '20412': 'Select the assignment submission that is being graded.',
  '20413': 'Only the student’s latest assignment submission can be graded.',
  '20414': 'A graded submission can be linked only to an assignment component.',
  '20419': 'This quiz attempt has already been submitted and cannot be changed.',
  '20421': 'This quiz attempt has already been submitted.',
}

const PHRASE_MESSAGES = [
  [/maximum quiz attempts have been used/i, 'You have used all attempts allowed for this quiz.'],
  [/quiz attempt exceeds max_attempts/i, 'You have used all attempts allowed for this quiz.'],
  [/quiz has not opened yet|cannot begin before open_at/i, 'This quiz has not opened yet.'],
  [/quiz is already closed|cannot begin after close_at/i, 'This quiz is already closed.'],
  [/student already has an open attempt/i, 'You already have an open attempt for this quiz. Reopen the quiz instead of starting another attempt.'],
  [/quiz duration has expired/i, 'The time limit for this quiz attempt has expired.'],
  [/quiz close_at has passed/i, 'The quiz closing time has passed, so this attempt can no longer be changed or submitted.'],
  [/quiz attempt has already been submitted/i, 'This quiz attempt has already been submitted.'],
  [/student is not enrolled in this quiz offering|not actively enrolled in the quiz offering/i, 'You are not enrolled in the class for this quiz.'],
  [/offering is not open for enrollment|direct enrollment is allowed only for an open/i, 'Enrollment is closed for this class.'],
  [/already enrolled|duplicate enrollment/i, 'You are already enrolled in this class.'],
  [/exceed.*capacity|capacity exceeded|reached.*capacity/i, 'This class has reached its enrollment capacity.'],
  [/instructor is not assigned/i, 'You are not assigned to this class.'],
  [/start the quiz attempt before loading quiz content/i, 'Start this quiz attempt to view its questions.'],
]

function cleanText(value) {
  if (value === null || value === undefined) return ''
  return String(value)
    .replace(/\\x00/g, '')
    .replace(/\u0000/g, '')
    .replace(/\0/g, '')
    .replace(/<[^>]{1,200}>/g, ' ')
    .replace(/&nbsp;/gi, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

export function extractOracleError(value) {
  const text = cleanText(value)
  const matches = [...text.matchAll(/ORA-(\d{5}):\s*([\s\S]*?)(?=\s*ORA-\d{5}:|\s*\[|$)/gi)]
  if (!matches.length) return null
  const primary = matches.find((m) => m[1] !== '06512') || matches[0]
  const code = primary[1]
  let message = cleanText(primary[2])
  message = message
    .replace(/\(?\d+\)?\s*\(SQLExecDirectW\).*$/i, '')
    .replace(/\s*at\s+"?[A-Z0-9_$#.]+"?,?\s*line\s*\d+.*$/i, '')
    .trim()
  return { code, message }
}

function looksTechnical(value) {
  const text = cleanText(value)
  return /\bHY\d{3}\b|\bODBC\b|SQLExec|pyodbc|Traceback|SystemError|UnicodeDecodeError|codec can(?:not|'t) decode|returned a result with an exception set|exception set|ORA-06512|EDUSPHERE_OWNER\.|Django Version|Request Method:|<html|<!doctype/i.test(text)
}

function phraseMessage(value) {
  const text = cleanText(value)
  for (const [pattern, message] of PHRASE_MESSAGES) {
    if (pattern.test(text)) return message
  }
  return ''
}

export function safeServerMessage(value, status = 0) {
  const text = cleanText(value)
  if (!text) return ''

  const oracle = extractOracleError(text)
  if (oracle) {
    if (ORACLE_MESSAGES[oracle.code]) return ORACLE_MESSAGES[oracle.code]
    const mapped = phraseMessage(oracle.message)
    if (mapped) return mapped
    if (oracle.message && !looksTechnical(oracle.message)) return oracle.message
    return status >= 500
      ? 'The server could not complete this request.'
      : 'The request could not be completed because of a database rule.'
  }

  const mapped = phraseMessage(text)
  if (mapped) return mapped
  if (looksTechnical(text) || text.length > 420) {
    if (status === 503) return 'The database service is temporarily unavailable. Please try again shortly.'
    if (status >= 500) return 'The server could not complete this request. Please try again.'
    return 'The request could not be completed. Please review the entered information and try again.'
  }
  return text
}


function validationMessage(body) {
  if (!body || typeof body !== 'object') return ''
  const parts = []
  const walk = (value, key = '') => {
    if (parts.length >= 4 || value === null || value === undefined) return
    if (Array.isArray(value)) { for (const item of value) walk(item, key); return }
    if (typeof value === 'object') {
      for (const [k, v] of Object.entries(value)) {
        if (['success','error_code','data'].includes(k)) continue
        walk(v, k)
      }
      return
    }
    const text = cleanText(value)
    if (!text) return
    const label = key && !['message','detail','error','non_field_errors'].includes(key)
      ? `${key.replace(/_/g, ' ')}: `
      : ''
    parts.push(`${label}${text}`)
  }
  walk(body)
  return parts.join(' · ')
}

function statusFallback(status) {
  if (status === 400) return 'The request could not be completed. Please review the entered information.'
  if (status === 401) return 'Your session is no longer valid. Please sign in again.'
  if (status === 403) return 'You do not have permission to perform this action.'
  if (status === 404) return 'The requested record could not be found.'
  if (status === 408) return 'The request timed out. Please try again.'
  if (status === 409) return 'This action conflicts with the current record state. Refresh and try again.'
  if (status === 429) return 'Too many requests were sent. Please wait a moment and try again.'
  if (status === 503) return 'The service is temporarily unavailable. Please try again shortly.'
  if (status >= 500) return 'The server could not complete this request. Please try again.'
  return 'Something went wrong while completing this request.'
}

export function normalizeApiError({ body, status = 0, fallback = '' } = {}) {
  const source = body?.message ?? body?.detail ?? body?.error ?? validationMessage(body) ?? fallback
  const serverMessage = cleanText(source)
  const oracle = extractOracleError(serverMessage)
  const message = safeServerMessage(serverMessage, status) || statusFallback(status)
  return {
    message,
    serverMessage,
    oracleCode: oracle?.code || null,
    backendCode: body?.error_code || null,
    status,
  }
}

export function userMessage(error, fallback = 'Something went wrong.') {
  if (!error) return fallback
  if (typeof error === 'string') return safeServerMessage(error) || fallback
  const normalized = normalizeApiError({
    body: error.body || { message: error.serverMessage || error.message },
    status: Number(error.status || 0),
    fallback: error.message || fallback,
  })
  return normalized.message || fallback
}

export function errorPresentation(error, context = '') {
  const status = Number(error?.status || 0)
  const message = userMessage(error)
  const oracleCode = error?.oracleCode || extractOracleError(error?.serverMessage || error?.message)?.code || null
  const network = error?.kind === 'network'
  const timeout = error?.kind === 'timeout'

  let title = 'Unable to complete this request'
  if (network) title = 'Cannot reach EduSphere'
  else if (timeout) title = 'Request timed out'
  else if (oracleCode === '20113' || /all attempts allowed/i.test(message)) title = 'No quiz attempts remaining'
  else if (oracleCode === '20110' || /has not opened yet/i.test(message)) title = 'Quiz not open yet'
  else if (oracleCode === '20111' || /quiz is already closed/i.test(message)) title = 'Quiz closed'
  else if (status === 403) title = 'Access denied'
  else if (status === 404) title = 'Not found'
  else if (status === 401) title = 'Sign-in required'
  else if (status >= 500) title = 'Something went wrong'

  if (context === 'quiz' && /already been submitted/i.test(message)) title = 'Attempt already submitted'

  const retryable = network || timeout || status === 408 || status === 429 || status >= 500
  return { title, message, status, oracleCode, retryable }
}

export function isQuizAttemptRequired(error) {
  const source = cleanText(error?.serverMessage || error?.message)
  return /start the quiz attempt before loading quiz content/i.test(source)
}
