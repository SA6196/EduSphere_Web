import { createRouter, createWebHistory } from 'vue-router'
import { auth } from '../stores/auth.js'

import LoginView from '../views/LoginView.vue'
import SignupView from '../views/SignupView.vue'
import ProfileView from '../views/ProfileView.vue'
import CatalogView from '../views/CatalogView.vue'
import OfferingWorkspaceView from '../views/OfferingWorkspaceView.vue'
import QuizAttemptView from '../views/student/QuizAttemptView.vue'
import StudentDashboardView from '../views/student/StudentDashboardView.vue'
import StudentPerformanceView from '../views/student/StudentPerformanceView.vue'
import StudentAttendanceView from '../views/student/StudentAttendanceView.vue'
import StudentQuizAttemptsView from '../views/student/StudentQuizAttemptsView.vue'
import InstructorDashboardView from '../views/instructor/InstructorDashboardView.vue'
import QuestionBankView from '../views/instructor/QuestionBankView.vue'
import QuizGradingView from '../views/instructor/QuizGradingView.vue'
import AdminDashboardView from '../views/admin/AdminDashboardView.vue'
import AdminReportsView from '../views/admin/AdminReportsView.vue'
import AdminManagementView from '../views/admin/AdminManagementView.vue'
import NotFoundView from '../views/NotFoundView.vue'
import { roleHome } from '../utils/roles.js'

const routes = [
  { path: '/', redirect: () => roleHome(auth.state.user?.role) },
  { path: '/login', name: 'login', component: LoginView, meta: { public: true } },
  { path: '/signup', name: 'signup', component: SignupView, meta: { public: true } },
  { path: '/profile', component: ProfileView },
  { path: '/catalog', component: CatalogView },
  { path: '/offerings/:offeringId', component: OfferingWorkspaceView },
  { path: '/student/dashboard', component: StudentDashboardView, meta: { roles: ['STUDENT'] } },
  { path: '/student/performance', component: StudentPerformanceView, meta: { roles: ['STUDENT'] } },
  { path: '/student/attendance', component: StudentAttendanceView, meta: { roles: ['STUDENT'] } },
  { path: '/student/quiz-attempts', component: StudentQuizAttemptsView, meta: { roles: ['STUDENT'] } },
  { path: '/student/quizzes/:quizId', component: QuizAttemptView, meta: { roles: ['STUDENT'] } },
  { path: '/instructor/dashboard', component: InstructorDashboardView, meta: { roles: ['INSTRUCTOR'] } },
  { path: '/question-bank', component: QuestionBankView, meta: { roles: ['INSTRUCTOR', 'ADMIN'] } },
  { path: '/instructor/quizzes/:quizId/grading', component: QuizGradingView, meta: { roles: ['INSTRUCTOR', 'ADMIN'] } },
  { path: '/admin/dashboard', component: AdminDashboardView, meta: { roles: ['ADMIN'] } },
  { path: '/admin/reports', component: AdminReportsView, meta: { roles: ['ADMIN'] } },
  { path: '/admin/management', component: AdminManagementView, meta: { roles: ['ADMIN'] } },
  { path: '/:pathMatch(.*)*', component: NotFoundView },
]


const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

router.beforeEach((to) => {
  if (to.meta.public) {
    if (to.path === '/login' && auth.state.user) return roleHome(auth.state.user.role)
    return true
  }

  if (!auth.state.user) return { path: '/login', query: { redirect: to.fullPath } }

  const roles = to.meta.roles
  if (roles && !roles.includes(auth.state.user.role)) return roleHome(auth.state.user.role)

  return true
})

export default router
