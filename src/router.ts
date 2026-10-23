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
          redirect: '/vlm/overview',
        },
        {
          path: 'vlm/overview',
          name: 'vlm-overview',
          component: () => import('@/views/vlm/VlmOverviewView.vue'),
          meta: { title: 'VLM 总览' },
        },
        {
          path: 'vlm/tasks',
          name: 'vlm-tasks',
          component: () => import('@/views/vlm/VlmTaskListView.vue'),
          meta: { title: '打标任务' },
        },
        {
          path: 'vlm/tasks/:taskId/items',
          name: 'vlm-task-items',
          component: () => import('@/views/vlm/VlmTaskItemListView.vue'),
          meta: { title: '任务执行明细' },
        },
        {
          path: 'vlm/prompts',
          name: 'vlm-prompts',
          component: () => import('@/views/vlm/VlmPromptManagementView.vue'),
          meta: { title: '提示词管理' },
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
