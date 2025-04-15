<template>
  <div class="space-y-6">
    <div v-for="post in posts" :key="post.id" class="card">
      <h2 class="text-2xl font-bold mb-2">
        <router-link :to="`/post/${post.slug}`" class="text-blue-600 hover:text-blue-800">
          {{ post.title }}
        </router-link>
      </h2>
      <div class="text-sm text-gray-600 mb-4">
        <span>By {{ post.author.username }}</span>
        <span class="mx-2">•</span>
        <span>{{ formatDate(post.published_date) }}</span>
        <span v-if="post.category" class="mx-2">•</span>
        <span v-if="post.category" class="text-blue-600">
          {{ post.category.name }}
        </span>
      </div>
      <p class="text-gray-700">{{ post.content.substring(0, 200) }}...</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'

const posts = ref([])

const formatDate = (dateString) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
}

onMounted(async () => {
  try {
    const response = await axios.get('http://localhost:8000/api/posts/')
    posts.value = response.data.results
  } catch (error) {
    console.error('Error fetching posts:', error)
  }
})
</script> 