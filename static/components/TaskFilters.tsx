import { TaskFilter, TaskSort } from '../types/task';
import { Button } from './ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from './ui/select';
import { Badge } from './ui/badge';

interface TaskFiltersProps {
  filter: TaskFilter;
  sort: TaskSort;
  onFilterChange: (filter: TaskFilter) => void;
  onSortChange: (sort: TaskSort) => void;
  stats: {
    total: number;
    active: number;
    completed: number;
  };
}

export function TaskFilters({ filter, sort, onFilterChange, onSortChange, stats }: TaskFiltersProps) {
  const filters: { value: TaskFilter; label: string; count: number }[] = [
    { value: 'all', label: 'Все', count: stats.total },
    { value: 'active', label: 'Активные', count: stats.active },
    { value: 'completed', label: 'Выполненные', count: stats.completed },
  ];

  return (
    <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between">
      <div className="flex gap-2 flex-wrap">
        {filters.map((f) => (
          <Button
            key={f.value}
            variant={filter === f.value ? 'default' : 'outline'}
            size="sm"
            onClick={() => onFilterChange(f.value)}
            className="gap-2"
          >
            {f.label}
            <Badge variant="secondary" className="bg-background text-foreground">
              {f.count}
            </Badge>
          </Button>
        ))}
      </div>
      
      <div className="flex items-center gap-2">
        <span className="text-sm text-muted-foreground">Сортировка:</span>
        <Select value={sort} onValueChange={(value: TaskSort) => onSortChange(value)}>
          <SelectTrigger className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="created">По дате создания</SelectItem>
            <SelectItem value="priority">По приоритету</SelectItem>
            <SelectItem value="title">По названию</SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>
  );
}