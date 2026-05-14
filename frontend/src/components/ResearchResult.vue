<template>
  <section class="panel panel-result" v-if="todoTasks.length || reportMarkdown || progressLogs.length">
    <header class="status-bar">
      <div class="status-main">
        <div class="status-chip" :class="{ active: loading }">
          <span class="dot"></span>
          {{ loading ? "研究进行中" : "研究流程完成" }}
        </div>
        <span class="status-meta">
          任务进度：{{ completedTasks }} / {{ totalTasks || todoTasks.length || 1 }}
          · 阶段记录 {{ progressLogs.length }} 条
        </span>
      </div>
      <div class="status-controls">
        <button class="secondary-btn" @click="logsCollapsed = !logsCollapsed">
          {{ logsCollapsed ? "展开流程" : "收起流程" }}
        </button>
      </div>
    </header>

    <div class="timeline-wrapper" v-show="!logsCollapsed && progressLogs.length">
      <transition-group name="timeline" tag="ul" class="timeline">
        <li v-for="(log, index) in progressLogs" :key="`${log}-${index}`">
          <span class="timeline-node"></span>
          <p>{{ log }}</p>
        </li>
      </transition-group>
    </div>

    <div class="tasks-section" v-if="todoTasks.length">
      <aside class="tasks-list">
        <h3>任务清单</h3>
        <ul>
          <li
            v-for="task in todoTasks"
            :key="task.id"
            :class="['task-item', { active: task.id === activeTaskId, completed: task.status === 'completed' }]"
          >
            <button type="button" class="task-button" @click="$emit('update:activeTaskId', task.id)">
              <span class="task-title">{{ task.title }}</span>
              <span class="task-status" :class="task.status">
                {{ formatTaskStatus(task.status) }}
              </span>
            </button>
            <p class="task-intent">{{ task.intent }}</p>
          </li>
        </ul>
      </aside>

      <article class="task-detail" v-if="currentTask">
        <header class="task-header">
          <div>
            <h3>{{ currentTaskTitle || "当前任务" }}</h3>
            <p class="muted" v-if="currentTaskIntent">
              {{ currentTaskIntent }}
            </p>
          </div>
          <div class="task-chip-group">
            <span class="chip chip-query" v-if="currentTaskQuery">搜索词：{{ currentTaskQuery }}</span>
          </div>
        </header>

        <section class="task-content">
          <div class="split-pane">
            <div class="pane log-pane">
              <h4>
                工具执行流
                <span class="pulse-indicator" v-if="toolHighlight"></span>
              </h4>
              <ul class="tool-logs" ref="logContainer">
                <li v-for="log in currentTaskToolCalls" :key="log.eventId" class="tool-call-card">
                  <div class="tool-call-header">
                    <span class="agent-tag">{{ log.agent }}</span>
                    <span class="tool-name">{{ log.tool }}</span>
                  </div>
                  <div class="tool-body">
                    <div class="tool-args" v-if="log.args && Object.keys(log.args).length > 0">
                      <div class="arg-item" v-for="(val, key) in log.args" :key="key">
                        <span class="arg-key">{{ key }}</span>:
                        <span class="arg-val">{{ val }}</span>
                      </div>
                    </div>
                    <div class="tool-result" v-if="log.result">
                      <pre><code>{{ log.result }}</code></pre>
                    </div>
                  </div>
                </li>
                <li v-if="!currentTaskToolCalls || currentTaskToolCalls.length === 0" class="muted hint-txt">
                  暂无工具调用...
                </li>
              </ul>
            </div>

            <div class="pane info-pane">
              <div class="info-block">
                <h4>
                  核心证据与线索
                  <span class="pulse-indicator" v-if="sourcesHighlight"></span>
                </h4>
                <ul class="source-list" v-if="currentTaskSources && currentTaskSources.length">
                  <li v-for="(src, idx) in currentTaskSources" :key="idx" class="source-item">
                    <a :href="src.url" target="_blank" rel="noopener">{{ src.title }}</a>
                    <p class="snippet">...{{ src.snippet }}...</p>
                  </li>
                </ul>
                <p v-else class="muted hint-txt">暂无搜集结果</p>
              </div>

              <div class="info-block" style="flex: 1">
                <h4>
                  子目标总结
                  <span class="pulse-indicator" v-if="summaryHighlight"></span>
                </h4>
                <div class="task-summary markdown-body" v-html="renderMarkdown(currentTaskSummary)"></div>
              </div>
            </div>
          </div>
        </section>
      </article>
    </div>

    <div class="report-section" v-if="reportMarkdown">
      <header class="report-header">
        <h3>
          📄 深度研究报告
          <span class="badge" v-if="loading">生成中...</span>
          <span class="badge success" v-else>已完成</span>
        </h3>
        <span class="pulse-indicator pulse-large" v-if="reportHighlight"></span>
      </header>
      <div class="markdown-body" v-html="renderMarkdown(reportMarkdown)"></div>
      <div class="report-raw">
        <h4>Markdown 原文</h4>
        <pre class="block-pre">{{ reportMarkdown }}</pre>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue';
import { marked } from 'marked';

const props = defineProps<{
  loading: boolean;
  totalTasks: number;
  completedTasks: number;
  progressLogs: string[];
  todoTasks: any[];
  activeTaskId: number | null;
  currentTask: any;
  currentTaskTitle?: string;
  currentTaskIntent?: string;
  currentTaskQuery?: string;
  currentTaskToolCalls?: any[];
  currentTaskSources?: any[];
  currentTaskSummary?: string;
  reportMarkdown: string;
  toolHighlight: boolean;
  sourcesHighlight: boolean;
  summaryHighlight: boolean;
  reportHighlight: boolean;
}>();

const emit = defineEmits<{
  (e: 'update:activeTaskId', id: number): void;
}>();

const logsCollapsed = ref(false);
const logContainer = ref<HTMLElement | null>(null);

const formatTaskStatus = (status: string) => {
  const map: Record<string, string> = {
    "not-started": "待处理",
    "in-progress": "执行中",
    completed: "已完成"
  };
  return map[status] || status;
};

const renderMarkdown = (text?: string) => {
  if (!text) return '<p class="muted hint-txt">汇总中...</p>';
  return marked.parse(text) || "";
};

watch(
  () => props.currentTaskToolCalls,
  () => {
    nextTick(() => {
      if (logContainer.value) {
        logContainer.value.scrollTop = logContainer.value.scrollHeight;
      }
    });
  },
  { deep: true }
);
</script>

<style scoped>
.panel-result {
  flex: 1;
  height: 100vh;
  padding: 24px;
  background: rgba(255, 255, 255, 0.95);
  border-radius: 0 20px 20px 0;
  border: 1px solid rgba(148, 163, 184, 0.18);
  display: flex;
  flex-direction: column;
  gap: 18px;
  overflow-y: auto;
  box-shadow: 0 24px 48px rgba(15, 23, 42, 0.12);
}

.status-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.status-main {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.status-controls {
  display: flex;
  gap: 8px;
}

.status-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: rgba(191, 219, 254, 0.28);
  padding: 8px 14px;
  border-radius: 999px;
  font-size: 13px;
  color: #1f2937;
  border: 1px solid rgba(59, 130, 246, 0.35);
  transition: background 0.3s ease, color 0.3s ease;
}

.status-chip.active {
  background: rgba(129, 140, 248, 0.2);
  border-color: rgba(129, 140, 248, 0.4);
  color: #1e293b;
}

.status-chip .dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: #2563eb;
  box-shadow: 0 0 12px rgba(37, 99, 235, 0.45);
  animation: pulse 1.8s ease-in-out infinite;
}

.status-meta {
  color: #64748b;
  font-size: 13px;
}

.secondary-btn {
  padding: 10px 18px;
  border-radius: 14px;
  background: rgba(148, 163, 184, 0.12);
  border: 1px solid rgba(148, 163, 184, 0.28);
  color: #1f2937;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease, color 0.2s ease;
}

.secondary-btn:hover {
  background: rgba(148, 163, 184, 0.2);
  border-color: rgba(148, 163, 184, 0.35);
  color: #0f172a;
}

.timeline-wrapper {
  max-height: 220px;
  overflow-y: auto;
  padding-right: 8px;
  scrollbar-width: thin;
  scrollbar-color: rgba(129, 140, 248, 0.45) rgba(226, 232, 240, 0.6);
}

.timeline-wrapper::-webkit-scrollbar {
  width: 6px;
}

.timeline-wrapper::-webkit-scrollbar-track {
  background: rgba(226, 232, 240, 0.6);
  border-radius: 999px;
}

.timeline-wrapper::-webkit-scrollbar-thumb {
  background: linear-gradient(180deg, rgba(129, 140, 248, 0.8), rgba(59, 130, 246, 0.7));
  border-radius: 999px;
}

.timeline-wrapper::-webkit-scrollbar-thumb:hover {
  background: linear-gradient(180deg, rgba(99, 102, 241, 0.9), rgba(37, 99, 235, 0.8));
}

.timeline {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
  position: relative;
  padding-left: 12px;
}

.timeline::before {
  content: "";
  position: absolute;
  top: 8px;
  bottom: 8px;
  left: 0;
  width: 2px;
  background: linear-gradient(180deg, rgba(59, 130, 246, 0.35), rgba(129, 140, 248, 0.15));
}

.timeline li {
  position: relative;
  padding-left: 24px;
  color: #1e293b;
  font-size: 14px;
  line-height: 1.5;
}

.timeline-node {
  position: absolute;
  left: -12px;
  top: 6px;
  width: 10px;
  height: 10px;
  border-radius: 999px;
  background: linear-gradient(135deg, #38bdf8, #7c3aed);
  box-shadow: 0 0 0 4px rgba(59, 130, 246, 0.22);
}

.timeline-enter-active,
.timeline-leave-active {
  transition: all 0.35s ease, opacity 0.35s ease;
}

.timeline-enter-from,
.timeline-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

.tasks-section {
  display: grid;
  grid-template-columns: 280px 1fr;
  gap: 20px;
  align-items: start;
}

@media (max-width: 960px) {
  .tasks-section {
    grid-template-columns: 1fr;
  }
}

.tasks-list {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(148, 163, 184, 0.26);
  border-radius: 18px;
  padding: 18px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  box-shadow: inset 0 0 0 1px rgba(226, 232, 240, 0.4);
}

.tasks-list h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
}

.tasks-list ul {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.task-item {
  border-radius: 14px;
  border: 1px solid transparent;
  transition: border-color 0.2s ease, background 0.2s ease;
}

.task-item.completed {
  border-color: rgba(56, 189, 248, 0.35);
  background: rgba(191, 219, 254, 0.28);
}

.task-item.active {
  border-color: rgba(129, 140, 248, 0.5);
  background: rgba(224, 231, 255, 0.5);
}

.task-button {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px 6px;
  background: transparent;
  border: none;
  color: inherit;
  cursor: pointer;
  text-align: left;
}

.task-title {
  font-weight: 600;
  font-size: 14px;
  color: #1e293b;
}

.task-status {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
  color: #1f2937;
  background: rgba(148, 163, 184, 0.2);
}

.task-status.pending {
  background: rgba(148, 163, 184, 0.18);
  color: #475569;
}

.task-status.in_progress {
  background: rgba(129, 140, 248, 0.24);
  color: #312e81;
}

.task-status.completed {
  background: rgba(34, 197, 94, 0.2);
  color: #15803d;
}

.task-status.skipped {
  background: rgba(248, 113, 113, 0.18);
  color: #b91c1c;
}

.task-intent {
  margin: 0;
  padding: 0 14px 12px 14px;
  font-size: 13px;
  color: #64748b;
}

.task-detail {
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(148, 163, 184, 0.26);
  border-radius: 18px;
  padding: 22px;
  display: flex;
  flex-direction: column;
  gap: 18px;
  box-shadow: inset 0 0 0 1px rgba(226, 232, 240, 0.5);
}

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  flex-wrap: wrap;
  gap: 12px;
}

.task-chip-group {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.task-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
}

.task-header .muted {
  margin: 6px 0 0;
}

.task-label {
  padding: 6px 12px;
  border-radius: 999px;
  background: rgba(191, 219, 254, 0.32);
  border: 1px solid rgba(59, 130, 246, 0.35);
  font-size: 12px;
  color: #1e3a8a;
}

.task-label.note-chip {
  background: rgba(34, 197, 94, 0.2);
  border-color: rgba(34, 197, 94, 0.35);
  color: #15803d;
}

.task-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.split-pane {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

@media (max-width: 768px) {
  .split-pane {
    grid-template-columns: 1fr;
  }
}

.pane {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.pane h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
  display: flex;
  align-items: center;
  gap: 8px;
}

.pulse-indicator {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #3b82f6;
  animation: pulse 1.5s ease-in-out infinite;
}

.pulse-indicator.pulse-large {
  width: 12px;
  height: 12px;
}

.tool-logs {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 300px;
  overflow-y: auto;
  padding-right: 8px;
}

.tool-call-card {
  background: rgba(248, 250, 252, 0.95);
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 14px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.tool-call-header {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: center;
}

.agent-tag {
  padding: 3px 10px;
  border-radius: 999px;
  background: rgba(129, 140, 248, 0.2);
  color: #312e81;
  font-size: 11px;
  font-weight: 600;
}

.tool-name {
  font-weight: 600;
  color: #1f2937;
  font-size: 13px;
}

.tool-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.tool-args {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  font-size: 12px;
}

.arg-key {
  font-weight: 600;
  color: #64748b;
}

.arg-val {
  color: #1f2937;
  word-break: break-all;
}

.tool-result {
  font-family: "JetBrains Mono", "Fira Code", monospace;
  font-size: 12px;
  background: rgba(226, 232, 240, 0.5);
  padding: 10px;
  border-radius: 10px;
  max-height: 150px;
  overflow-y: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

.tool-result pre {
  margin: 0;
}

.info-block {
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 16px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.source-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.source-item {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.source-item a {
  color: #2563eb;
  text-decoration: none;
  font-weight: 600;
  font-size: 13px;
  transition: color 0.2s ease;
}

.source-item a:hover {
  color: #0f172a;
}

.source-item a::after {
  content: " ↗";
  font-size: 11px;
  opacity: 0.6;
}

.source-item .snippet {
  margin: 0;
  font-size: 12px;
  color: #64748b;
  line-height: 1.5;
}

.task-summary {
  font-size: 14px;
  line-height: 1.7;
  color: #1f2937;
}

.task-summary :deep(h1),
.task-summary :deep(h2),
.task-summary :deep(h3) {
  margin: 16px 0 8px;
}

.task-summary :deep(p) {
  margin: 0 0 8px;
}

.task-summary :deep(ul),
.task-summary :deep(ol) {
  margin: 8px 0;
  padding-left: 20px;
}

.hint-txt {
  color: #64748b;
  font-size: 13px;
  text-align: center;
  padding: 20px;
}

.muted {
  color: #64748b;
}

.report-section {
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(148, 163, 184, 0.26);
  border-radius: 18px;
  padding: 22px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.report-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
}

.report-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #1f2937;
  display: flex;
  align-items: center;
  gap: 10px;
}

.report-header .badge {
  padding: 4px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 500;
  background: rgba(59, 130, 246, 0.2);
  color: #1e3a8a;
}

.report-header .badge.success {
  background: rgba(34, 197, 94, 0.2);
  color: #15803d;
}

.markdown-body {
  font-size: 15px;
  line-height: 1.8;
  color: #1f2937;
}

.markdown-body :deep(h1) {
  font-size: 24px;
  margin: 24px 0 16px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(148, 163, 184, 0.2);
}

.markdown-body :deep(h2) {
  font-size: 20px;
  margin: 20px 0 12px;
}

.markdown-body :deep(h3) {
  font-size: 16px;
  margin: 16px 0 8px;
}

.markdown-body :deep(p) {
  margin: 0 0 12px;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin: 12px 0;
  padding-left: 24px;
}

.markdown-body :deep(li) {
  margin: 6px 0;
}

.markdown-body :deep(code) {
  background: rgba(148, 163, 184, 0.2);
  padding: 2px 6px;
  border-radius: 6px;
  font-family: "JetBrains Mono", monospace;
  font-size: 13px;
}

.markdown-body :deep(pre) {
  background: rgba(248, 250, 252, 0.9);
  padding: 16px;
  border-radius: 14px;
  overflow-x: auto;
}

.markdown-body :deep(pre code) {
  background: none;
  padding: 0;
}

.report-raw {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid rgba(148, 163, 184, 0.2);
}

.report-raw h4 {
  margin: 0 0 12px;
  font-size: 14px;
  font-weight: 600;
  color: #64748b;
}

.block-pre {
  font-family: "JetBrains Mono", "Fira Code", ui-monospace, monospace;
  font-size: 13px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
  color: #1f2937;
  background: rgba(248, 250, 252, 0.9);
  padding: 16px;
  border-radius: 14px;
  border: 1px solid rgba(148, 163, 184, 0.35);
  overflow: auto;
  max-height: 420px;
}

@keyframes pulse {
  0%, 100% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.3);
    opacity: 0.5;
  }
}

@keyframes glow {
  0% {
    box-shadow: 0 0 0 rgba(59, 130, 246, 0.3);
    border-color: rgba(59, 130, 246, 0.5);
  }
  100% {
    box-shadow: inset 0 0 0 1px rgba(59, 130, 246, 0.12);
    border-color: rgba(148, 163, 184, 0.2);
  }
}

.block-highlight {
  animation: glow 1.2s ease;
}

@media (max-width: 960px) {
  .panel-result {
    padding: 18px;
  }

  .status-bar {
    flex-direction: column;
    align-items: flex-start;
  }

  .status-main,
  .status-controls {
    width: 100%;
  }

  .status-controls {
    justify-content: flex-start;
  }
}
</style>
