// frontend/src/utils/dateUtils.js
export const formatLocalTime = (isoString) => {
  const date = new Date(isoString);
  
  // Опции для форматирования в часовом поясе Алматы
  const options = {
    timeZone: 'Asia/Almaty',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  };
  
  return date.toLocaleString('ru-RU', options);
};

export const formatTime = (isoString) => {
  const date = new Date(isoString);
  
  const options = {
    timeZone: 'Asia/Almaty',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false
  };
  
  return date.toLocaleTimeString('ru-RU', options);
};

export const getRelativeTime = (isoString) => {
  const date = new Date(isoString);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  
  if (diffMins < 1) return 'только что';
  if (diffMins < 60) return `${diffMins} мин. назад`;
  
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours} ч. назад`;
  
  const diffDays = Math.floor(diffHours / 24);
  return `${diffDays} дн. назад`;
};