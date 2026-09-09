import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Badge, EmptyState, ErrorState, FormActions, LoadingState, Modal, PageHeader, Panel, formatDate, submitObject, titleCase } from "../components/Workspace";
import { useAuth } from "../features/auth/AuthProvider";
import { createObjective, createTask, listObjectives, listTasks, updateTask } from "../features/operations/api";
import type { Objective, WorkTask } from "../features/operations/types";

const taskStages = ["backlog", "todo", "in_progress", "blocked", "review", "done"];

export function CompanyPage() {
  const { user } = useAuth();
  const [modal, setModal] = useState<"objective" | "task" | null>(null);
  const objectives = useQuery({ queryKey: ["objectives"], queryFn: listObjectives });
  const tasks = useQuery({ queryKey: ["tasks"], queryFn: listTasks });
  const canWriteTask = Boolean(user?.permissions.some((permission) => ["task:write", "task:write_own"].includes(permission)));
  const canWriteObjective = Boolean(user?.permissions.includes("objective:write"));
  const loading = objectives.isLoading || tasks.isLoading;
  const error = objectives.error ?? tasks.error;
  return <div className="workspace-page wide-page">
    <PageHeader eyebrow="Company alignment" title="Company" description="Objectives connect weekly priorities to accountable execution across every team." actions={<div className="button-row">{canWriteObjective && <button className="button subtle" type="button" onClick={() => setModal("objective")}>New objective</button>}{canWriteTask && <button className="button primary" type="button" onClick={() => setModal("task")}>New task</button>}</div>} />
    {loading && <LoadingState label="Loading company priorities" />}
    {error && <ErrorState error={error} retry={() => { void objectives.refetch(); void tasks.refetch(); }} />}
    {objectives.data && <Panel title="Objectives" subtitle="Owned outcomes and measurable progress">{objectives.data.items.length ? <div className="objective-grid">{objectives.data.items.map((item) => <article key={item.id}><header><Badge tone={item.status === "completed" ? "good" : "gold"}>{titleCase(item.status)}</Badge><span>{titleCase(item.department)}</span></header><h3>{item.title}</h3><p>{item.description ?? "No description"}</p><div className="progress-label"><span>{item.owner_name ?? "Unassigned"}</span><strong>{item.progress}%</strong></div><div className="progress"><i style={{ width: `${Math.min(100, Math.max(0, item.progress))}%` }} /></div><footer>Due {formatDate(item.due_date)}</footer></article>)}</div> : <EmptyState title="No company objectives" description="Create an objective to align work across departments." />}</Panel>}
    {tasks.data && <Panel title="Task board" subtitle="A lightweight view of accountable work"><TaskBoard tasks={tasks.data.items} editable={canWriteTask} /></Panel>}
    <CreateCompanyModal kind={modal} onClose={() => setModal(null)} objectives={objectives.data?.items ?? []} />
  </div>;
}

function TaskBoard({ tasks, editable }: { tasks: WorkTask[]; editable: boolean }) {
  const queryClient = useQueryClient();
  const move = useMutation({ mutationFn: ({ id, status }: { id: string; status: string }) => updateTask(id, { status }), onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["tasks"] }) });
  if (!tasks.length) return <EmptyState title="No tasks yet" description="Create the first task and assign an owner and due date." />;
  return <div className="task-board">{taskStages.map((stage) => <section key={stage}><header><strong>{titleCase(stage)}</strong><span>{tasks.filter((item) => item.status === stage).length}</span></header><div>{tasks.filter((item) => item.status === stage).map((task) => <article key={task.id}><div><Badge tone={task.priority === "P0" ? "bad" : task.priority === "P1" ? "warn" : "neutral"}>{task.priority.toUpperCase()}</Badge><span>{titleCase(task.department)}</span></div><h3>{task.title}</h3><p>{task.owner_name ?? task.owner_id ?? "Unassigned"}</p><footer><span>{formatDate(task.due_date)}</span>{editable && stage !== "done" && <button type="button" disabled={move.isPending} onClick={() => move.mutate({ id: task.id, status: taskStages[Math.min(taskStages.length - 1, taskStages.indexOf(stage) + 1)] })}>Advance →</button>}</footer></article>)}</div></section>)}</div>;
}

function CreateCompanyModal({ kind, onClose, objectives }: { kind: "objective" | "task" | null; onClose: () => void; objectives: Objective[] }) {
  const queryClient = useQueryClient();
  const mutation = useMutation<Objective | WorkTask, Error, Partial<Objective> | Partial<WorkTask> >({ mutationFn: (value) => kind === "objective" ? createObjective(value as Partial<Objective>) : createTask(value as Partial<WorkTask>), onSuccess: () => { onClose(); void queryClient.invalidateQueries({ queryKey: kind === "objective" ? ["objectives"] : ["tasks"] }); } });
  return <Modal title={kind === "objective" ? "New objective" : "New task"} open={kind !== null} onClose={onClose}><form className="record-form" onSubmit={(event) => { const value = submitObject(event); mutation.mutate(kind === "objective" ? { ...value, progress: Number(value.progress ?? 0) } : value); }}>
    <label className="span-two">Title<input name="title" required autoFocus /></label><label className="span-two">Description<textarea name="description" rows={3} /></label>
    {kind === "objective" ? <><label>Owner staff ID<input name="owner_id" required /></label><label>Workstream<select name="department"><option value="company">Company</option><option value="sales">Sales</option><option value="argus">ARGUS</option><option value="lynx">LYNX</option><option value="coding">Coding</option><option value="legal">Legal</option><option value="finance">Finance</option></select></label><label>Status<select name="status"><option value="planned">Planned</option><option value="active">Active</option><option value="at_risk">At risk</option><option value="completed">Completed</option></select></label><label>Start date<input name="start_date" type="date" required /></label><label>Due date<input name="due_date" type="date" /></label><label>Progress %<input name="progress" type="number" min="0" max="100" defaultValue="0" /></label></> : <><label>Objective<select name="objective_id"><option value="">No objective</option>{objectives.map((item) => <option key={item.id} value={item.id}>{item.title}</option>)}</select></label><label>Workstream<select name="department"><option value="company">Company</option><option value="sales">Sales</option><option value="argus">ARGUS</option><option value="lynx">LYNX</option><option value="coding">Coding</option><option value="legal">Legal</option><option value="finance">Finance</option></select></label><label>Priority<select name="priority"><option value="P0">P0 — Critical</option><option value="P1">P1 — High</option><option value="P2">P2 — Normal</option><option value="P3">P3 — Low</option></select></label><label>Status<select name="status"><option value="backlog">Backlog</option><option value="todo">To do</option><option value="in_progress">In progress</option></select></label><label>Owner staff ID<input name="owner_id" required /></label><label>Due date<input name="due_date" type="date" /></label></>}
    {mutation.isError && <div className="form-error">{mutation.error.message}</div>}<FormActions saving={mutation.isPending} onCancel={onClose} />
  </form></Modal>;
}
