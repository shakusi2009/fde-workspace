import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = createRouter({
  history: createWebHistory(),
  scrollBehavior: () => ({ top: 0 }),
  routes: [
    {
      path: '/login',
      name: 'login',
      component: () => import('@/views/LoginView.vue'),
      meta: { public: true },
    },
    {
      path: '/',
      component: () => import('@/layout/AppLayout.vue'),
      children: [
        {
          path: '',
          name: 'overview',
          component: () => import('@/views/OverviewView.vue'),
          meta: { title: '工作台' },
        },
        {
          path: 'account/users',
          name: 'users',
          component: () => import('@/views/UsersView.vue'),
          meta: { title: '用户管理', permission: 'account_center' },
        },
        {
          path: 'account/roles',
          name: 'roles',
          component: () => import('@/views/RolesView.vue'),
          meta: { title: '角色管理', permission: 'account_center' },
        },
        {
          path: 'vlm',
          name: 'vlm',
          component: () => import('@/views/PlaceholderView.vue'),
          props: {
            type: 'vlm',
            title: '智驾 VLM 业务',
            description: '面向智能驾驶场景的视觉语言模型业务空间',
          },
          meta: { title: '智驾 VLM 业务' },
        },
        {
          path: 'agents',
          name: 'agents',
          component: () => import('@/views/PlaceholderView.vue'),
          props: {
            type: 'agent',
            title: '智能体开发',
            description: '编排、调试和评估汽车业务智能体',
          },
          meta: { title: '智能体开发', permission: 'agent_center' },
        },
      ],
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (!auth.ready) await auth.restore()

  if (to.meta.public) {
    return auth.isAuthenticated && to.name === 'login' ? { name: 'overview' } : true
  }
  if (!auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  const permission = to.meta.permission as string | undefined
  if (permission && !auth.can(permission)) {
    return { name: 'overview' }
  }
  return true
})

export default router
