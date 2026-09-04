<template>
  <div class="comment-box">
    <!-- 보안 위반(의도적): 사용자 입력을 검증/이스케이프 없이 v-html에 그대로 바인딩 (XSS) -->
    <div v-html="userComment"></div>
  </div>
</template>

<script>
export default {
  name: 'CommentBox',
  props: {
    userComment: {
      type: String,
      default: ''
    }
  }
}
</script>
