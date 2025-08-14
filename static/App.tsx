import { useTasks } from "./hooks/useTasks";
import { TaskForm } from "./components/TaskForm";
import { TaskItem } from "./components/TaskItem";
import { TaskFilters } from "./components/TaskFilters";
import { Card } from "./components/ui/card";
import { CheckCircle2, ListTodo } from "lucide-react";

export default function App() {
  const {
    tasks,
    stats,
    filter,
    sort,
    setFilter,
    setSort,
    addTask,
    updateTask,
    deleteTask,
    toggleTask,
  } = useTasks();

  return (
    <div className="min-h-screen bg-muted/30">
      <div className="container mx-auto px-4 py-8 max-w-4xl">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-2">
            <ListTodo className="h-8 w-8 text-primary" />
            <h1 className="text-3xl">Менеджер задач</h1>
          </div>
          <p className="text-muted-foreground">
            Организуйте свои задачи и отслеживайте прогресс
          </p>
        </div>

        {/* Stats Overview */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
          <Card className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-100 rounded-lg">
                <ListTodo className="h-5 w-5 text-blue-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">
                  Всего задач
                </p>
                <p className="text-2xl">{stats.total}</p>
              </div>
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-orange-100 rounded-lg">
                <ListTodo className="h-5 w-5 text-orange-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">
                  Активных
                </p>
                <p className="text-2xl">{stats.active}</p>
              </div>
            </div>
          </Card>

          <Card className="p-4">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-100 rounded-lg">
                <CheckCircle2 className="h-5 w-5 text-green-600" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">
                  Выполнено
                </p>
                <p className="text-2xl">{stats.completed}</p>
              </div>
            </div>
          </Card>
        </div>

        {/* Task Creation and Filters */}
        <Card className="p-6 mb-6">
          <div className="flex flex-col sm:flex-row gap-4 items-start sm:items-center justify-between mb-6">
            <TaskForm onSubmit={addTask} />
          </div>

          <TaskFilters
            filter={filter}
            sort={sort}
            onFilterChange={setFilter}
            onSortChange={setSort}
            stats={stats}
          />
        </Card>

        {/* Task List */}
        <div className="space-y-4">
          {tasks.length === 0 ? (
            <Card className="p-12 text-center">
              <ListTodo className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <h3 className="mb-2">Нет задач</h3>
              <p className="text-muted-foreground mb-4">
                {filter === "completed" && stats.completed === 0
                  ? "У вас пока нет выполненных задач"
                  : filter === "active" && stats.active === 0
                    ? "Все задачи выполнены! Отличная работа!"
                    : "Создайте свою первую задачу, чтобы начать"}
              </p>
              {filter !== "active" &&
                stats.active === 0 &&
                stats.total > 0 && (
                  <TaskForm onSubmit={addTask} />
                )}
            </Card>
          ) : (
            tasks.map((task) => (
              <TaskItem
                key={task.id}
                task={task}
                onToggle={toggleTask}
                onUpdate={updateTask}
                onDelete={deleteTask}
              />
            ))
          )}
        </div>

        {/* Progress Bar */}
        {stats.total > 0 && (
          <Card className="p-4 mt-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm">
                Прогресс выполнения
              </span>
              <span className="text-sm text-muted-foreground">
                {stats.completed} из {stats.total} задач
              </span>
            </div>
            <div className="w-full bg-muted rounded-full h-2">
              <div
                className="bg-primary h-2 rounded-full transition-all duration-300"
                style={{
                  width: `${(stats.completed / stats.total) * 100}%`,
                }}
              />
            </div>
          </Card>
        )}
      </div>
    </div>
  );
}