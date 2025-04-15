<script setup>
import { ref, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'

const posts = ref([])
const loading = ref(true)
const route = useRoute()
const router = useRouter()

const fetchPosts = async () => {
  try {
    loading.value = true
    const params = new URLSearchParams()
    if (route.query.search) params.append('search', route.query.search)
    if (route.query.category) params.append('category', route.query.category)
    if (route.query.tag) params.append('tag', route.query.tag)
    
    const response = await axios.get(`/api/posts/?${params.toString()}`)
    posts.value = response.data
  } catch (error) {
    console.error('Error fetching posts:', error)
  } finally {
    loading.value = false
  }
}

// Watch for route query changes
watch(() => route.query, () => {
  fetchPosts()
})

onMounted(() => {
  fetchPosts()
})
</script>

<template>
  <div>
    <div v-if="loading" class="text-center py-8">
      <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
    </div>
    
    <div v-else-if="posts.length === 0" class="text-center py-8">
      <p class="text-gray-500 dark:text-gray-400">No posts found.</p>
    </div>
    
    <div v-else class="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
      <div v-for="post in posts" :key="post.id" class="bg-white dark:bg-gray-800 rounded-lg shadow-md overflow-hidden">
        <div class="p-6">
          <h2 class="text-xl font-semibold text-gray-900 dark:text-white mb-2">
            <router-link :to="`/post/${post.id}`" class="hover:text-blue-600 dark:hover:text-blue-400">
              {{ post.title }}
            </router-link>
          </h2>
          
          <div class="flex items-center text-sm text-gray-500 dark:text-gray-400 mb-4">
            <span>{{ new Date(post.created_at).toLocaleDateString() }}</span>
            <span class="mx-2">•</span>
            <router-link 
              :to="`/?category=${post.category.slug}`" 
              class="hover:text-blue-600 dark:hover:text-blue-400"
            >
              {{ post.category.name }}
            </router-link>
          </div>
          
          <div class="flex flex-wrap gap-2 mb-4">
            <router-link
              v-for="tag in post.tags"
              :key="tag.id"
              :to="`/?tag=${tag.slug}`"
              class="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 rounded-full hover:bg-gray-200 dark:hover:bg-gray-600"
            >
              {{ tag.name }}
            </router-link>
          </div>
          
          <p class="text-gray-600 dark:text-gray-300 line-clamp-3">{{ post.content }}</p>
        </div>
      </div>
    </div>
  </div>
</template> 