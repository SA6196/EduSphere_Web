export function roleHome(role) {
  if (role === 'STUDENT') return '/student/dashboard'
  if (role === 'INSTRUCTOR') return '/instructor/dashboard'
  if (role === 'ADMIN') return '/admin/dashboard'
  return '/login'
}
