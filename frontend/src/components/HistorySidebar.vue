<template>
  <aside class="history-sidebar">
    <div class="sidebar-header">
      <h2>📚 历史研究</h2>
      <button class="new-btn" @click="$emit('new-research')" title="开启新研究">
        + 新建
      </button>
    </div>
    <div class="history-list">
      <p v-if="isLoading" class="muted">加载中...</p>
      <p v-else-if="!sessions.length" class="muted">尚未进行过研究，赶快开始吧！</p>
      <ul v-else class="h-list">
        <li v-for="session in sessions" :key="session.id" 
            class="history-item" @click="$emit('select-session', session.id)">
          <div class="history-topic">{{ session.topic }}</div>
          <div class="history-meta">
            <span class="status" :class="session.status">{{ session.status === 'completed' ? '已完成' : session.status }}</span>
            <span class="time">{{ new Date(session.created_at).toLocaleDateString() }}</span>
          </div>
        </li>
      </ul>
    </div>
  </aside>
</template>

<script setup lang="ts">
import type { ResearchSession } from '../services/api';

defineProps<{
  sessions: ResearchSession[];
  isLoading: boolean;
}>();

defineEmits<{
  (e: 'select-session', id: string): void;
  (e: 'new-research'): void;
}>();
</script>

<style scoped>
.history-sidebar {
  width: 280px;
  min-width: 280px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 20px 0 0 20px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  padding: 24px;
  display: flex;
  flex-direction: column;
  gap: 20px;
  box-shadow: 0 24px 48px rgba(15, 23, 42, 0.12);
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.sidebar-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
}

.new-btn {
  padding: 8px 14px;
  background: linear-gradient(135deg, #2563eb, #7c3aed);
  border: none;
  border-radius: 10px;
  color: white;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: transform 0.2s, box-shadow 0.2s;
}

.new-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
}

.history-list {
  flex: 1;
  overflow-y: auto;
}

.history-list .muted {
  color: #64748b;
  font-size: 14px;
  text-align: center;
  padding: 20px 0;
}

.h-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.history-item {
  padding: 14px 16px;
  background: rgba(248, 250, 252, 0.9);
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 14px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.history-item:hover {
  background: rgba(224, 231, 255, 0.5);
  border-color: rgba(129, 140, 248, 0.4);
  transform: translateX(4px);
}

.history-topic {
  font-weight: 600;
  font-size: 14px;
  color: #1f2937;
  margin-bottom: 8px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.history-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 12px;
}

.history-meta .status {
  padding: 3px 10px;
  border-radius: 999px;
  font-weight: 500;
}

.history-meta .status.completed {
  background: rgba(34, 197, 94, 0.2);
  color: #15803d;
}

.history-meta .status.in_progress {
  background: rgba(129, 140, 248, 0.24);
  color: #312e81;
}

.history-meta .status.pending {
  background: rgba(148, 163, 184, 0.18);
  color: #475569;
}

.history-meta .time {
  color: #64748b;
}

@media (max-width: 768px) {
  .history-sidebar {
    width: 100%;
    min-width: 100%;
    border-radius: 16px;
    max-height: 200px;
  }
}
</style>
