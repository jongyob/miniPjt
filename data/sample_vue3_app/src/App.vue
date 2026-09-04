<template>
  <div id="app">
    <comment-box :user-comment="comment" />
  </div>
</template>

<script>
import CommentBox from './components/CommentBox.vue'

export default {
  name: 'App',
  components: { CommentBox },
  data() {
    return {
      comment: '<b>example</b>'
    }
  }
}
</script>
