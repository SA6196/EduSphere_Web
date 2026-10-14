const FRIENDLY_LABELS = {
  Y: 'Yes',
  N: 'No',
  ACTIVE: 'Active',
  INACTIVE: 'Inactive',
  OPEN: 'Open',
  PLANNED: 'Planned',
  ENROLLED: 'Enrolled',
  WAITLISTED: 'Waitlisted',
  COMPLETED: 'Completed',
  CANCELLED: 'Cancelled',
  PRESENT: 'Present',
  ABSENT: 'Absent',
  LATE: 'Late',
  EXCUSED: 'Excused',
  LOW: 'Low',
  NORMAL: 'Normal',
  MEDIUM: 'Medium',
  HIGH: 'High',
  URGENT: 'Urgent',
  MIDTERM: 'Midterm',
  FINAL: 'Final',
  PRACTICAL: 'Practical',
  INTERNAL: 'Internal',
  MAKEUP: 'Make-up',
  LECTURE: 'Lecture',
  LAB: 'Laboratory',
  TUTORIAL: 'Tutorial',
  REVIEW: 'Review',
  PDF: 'PDF',
  PPT: 'PowerPoint',
  DOC: 'Document',
  VIDEO: 'Video',
  LINK: 'Web Link',
  NOTE: 'Notes',
  LAB_MANUAL: 'Lab Manual',
  MCQ_SINGLE: 'Single-answer MCQ',
  MCQ_MULTI: 'Multiple-answer MCQ',
  TRUE_FALSE: 'True / False',
  SHORT_TEXT: 'Short Answer',
  FILL_BLANK: 'Fill in the Blank',
  LONG_TEXT: 'Long Answer',
  ASSIGNMENT: 'Assignment',
  QUIZ: 'Quiz',
  EXAM: 'Exam',
  OTHER: 'Other',
  CONFIGURED: 'Configured',
  SENT: 'Sent',
}

export const EXAM_TYPES = ['MIDTERM', 'FINAL', 'PRACTICAL', 'INTERNAL', 'MAKEUP', 'OTHER']
export const SESSION_TYPES = ['LECTURE', 'LAB', 'TUTORIAL', 'REVIEW', 'OTHER']
export const MATERIAL_TYPES = ['PDF', 'PPT', 'DOC', 'VIDEO', 'LINK', 'NOTE', 'LAB_MANUAL', 'OTHER']
export const QUESTION_TYPES = ['MCQ_SINGLE','MCQ_MULTI','TRUE_FALSE','MATCHING','ORDERING','NUMERICAL','SHORT_TEXT','FILL_BLANK','LONG_TEXT']
export const ATTENDANCE_STATUSES = ['PRESENT', 'ABSENT', 'LATE', 'EXCUSED']

export function displayLabel(value) {
  if (value === null || value === undefined || value === '') return '—'
  const raw = String(value)
  if (FRIENDLY_LABELS[raw.toUpperCase()]) return FRIENDLY_LABELS[raw.toUpperCase()]
  return raw.replaceAll('_', ' ').toLowerCase().replace(/\b\w/g, (c) => c.toUpperCase()).replace(/\bId\b/g, 'ID').replace(/\bNo\b/g, 'No.')
}

export function titleCase(value) {
  return displayLabel(value)
}

export function formatDate(value) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return String(value)
  return new Intl.DateTimeFormat('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
  }).format(d)
}

export function formatDateTime(value) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return String(value)
  return new Intl.DateTimeFormat('en-IN', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  }).format(d)
}

export function compactNumber(value) {
  if (value === null || value === undefined) return '—'
  return new Intl.NumberFormat('en-IN', { maximumFractionDigits: 2 }).format(Number(value))
}

export function percent(value) {
  if (value === null || value === undefined) return '—'
  return `${Number(value).toFixed(1)}%`
}

export function safeArray(value) {
  return Array.isArray(value) ? value : []
}
