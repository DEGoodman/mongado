<template>
  <div v-if="post" class="card">
    <h1 class="text-3xl font-bold mb-4 text-gray-900">{{ post.title }}</h1>
    <div class="text-sm text-gray-600 mb-6">
      <span>By {{ post.author.username }}</span>
      <span class="mx-2">•</span>
      <span>{{ formatDate(post.published_date) }}</span>
      <span v-if="post.category" class="mx-2">•</span>
      <span v-if="post.category" class="text-blue-600">
        {{ post.category.name }}
      </span>
    </div>
    <div class="prose max-w-none text-gray-800" v-html="formatContent(post.content)"></div>
    <!-- Debug information -->
    <div class="mt-8 p-4 bg-gray-100 rounded">
      <h3 class="font-bold mb-2">Debug Information:</h3>
      <pre class="text-xs">{{ JSON.stringify(post, null, 2) }}</pre>
    </div>
  </div>
  <div v-else class="text-center py-8">
    <p class="text-gray-600">Loading post...</p>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import axios from 'axios'

const route = useRoute()
const post = ref(null)

const formatDate = (dateString) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
}

const formatContent = (content) => {
  // Simple markdown-like formatting
  return content
    .replace(/\n/g, '<br>')
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
}

onMounted(async () => {
  try {
    console.log('Fetching post with slug:', route.params.slug)
    const response = await axios.get(`http://localhost:8000/api/posts/${route.params.slug}/`)
    console.log('API Response:', response.data)
    post.value = response.data
  } catch (error) {
    console.error('Error fetching post:', error)
    console.error('Error details:', error.response?.data)
  }
})
</script> 