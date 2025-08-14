export interface Task {
  id: string;
  title: string;
  description?: string;
  completed: boolean;
  priority: 'low' | 'medium' | 'high';
  createdAt: Date;
  updatedAt: Date;
}

export type TaskFilter = 'all' | 'active' | 'completed';
export type TaskSort = 'created' | 'priority' | 'title';