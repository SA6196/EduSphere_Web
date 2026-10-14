import { createApp } from 'vue'
import App from './App.vue'
import router from './router/index.js'
import { auth } from './stores/auth.js'
import { toast } from './stores/toast.js'
import { userMessage } from './utils/errors.js'
import './styles/main.css'

window.addEventListener('unhandledrejection', (event) => {
  const reason = event.reason
  if (reason?.kind === 'cancelled') return
  toast.error(userMessage(reason, 'An unexpected frontend error occurred.'))
})

await auth.bootstrap()

createApp(App)
  .use(router)
  .mount('#app')
