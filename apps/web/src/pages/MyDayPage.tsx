import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";

import { Badge, EmptyState, ErrorState, FormActions, LoadingState, Modal, PageHeader, Panel, formatDate, submitObject, titleCase } from "../components/Workspace";
import { createActivity, getMyDay, updateActivity } from "../features/operations/api";
import type { Activity } from "../features/operations/types";

function ActivityRow({ item, onComplete }: { item: Activity; onComplete?: (item: Activity) => void }) {
  return <article className="activity-row">
    <div className="activity-icon" aria-hidden="true">{item.activity_type === "meeting" ? "M" : item.activity_type === "call" ? "C" : "↗"}</div>
    <div><strong>{item.account_name ?? item.next_action ?? titleCase(item.activity_type)}</strong><p>{item.next_action ?? item.notes ?? "No notes added"}</p></div>
    <div className="activity-meta"><span>{formatDate(item.next_action_at ?? item.started_at, true)}</span><Badge tone={item.next_action_at && new Date(item.next_action_at) < new Date() ? "bad" : "neutral"}>{titleCase(item.activity_type)}</Badge></div>
    {onComplete && !item.completed_at && <button className="button subtle compact" type="button" onClick={() => onComplete(item)}>Complete</button>}
  </article>;
}

export function MyDayPage() {
  const queryClient = useQueryClient();
  const [activityOpen, setActivityOpen] = useState(false);
  const query = useQuery({ queryKey: ["my-day"], queryFn: getMyDay });
  const complete = useMutation({
    mutationFn: (item: Activity) => updateActivity(item.id, { completed_at: new Date().toISOString() }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ["my-day"] }),
  });
  const create = useMutation({
    mutationFn: createActivity,
    onSuccess: () => { setActivityOpen(false); void queryClient.invalidateQueries({ queryKey: ["my-day"] }); },
  });

  const data = query.data;
  const priority = [...(data?.overdue ?? []), ...(data?.follow_ups_today ?? [])];
  return <div className="workspace-page">
    <PageHeader eyebrow="Sales command center" title="My Day" description="The next best actions, meetings and newly assigned leads—ordered for action." actions={<button className="button primary" type="button" onClick={() => setActivityOpen(true)}>Log activity</button>} />
    {query.isLoading && <LoadingState label="Building your day" />}
    {query.isError && <ErrorState error={query.error} retry={() => void query.refetch()} />}
    {data && <div className="my-day-grid">
      <Panel title="Next actions" subtitle={`${data.overdue.length} overdue · ${data.follow_ups_today.length} due today`} className="span-two">
        {priority.length ? <div className="activity-list">{priority.map((item) => <ActivityRow key={item.id} item={item} onComplete={(value) => complete.mutate(value)} />)}</div> : <EmptyState title="You're caught up" description="There are no overdue or due-today follow-ups." />}
      </Panel>
      <Panel title="Today's meetings" subtitle="Upcoming conversations">
        {data.meetings.length ? <div className="activity-list compact-list">{data.meetings.map((item) => <ActivityRow key={item.id} item={item} />)}</div> : <EmptyState title="No meetings scheduled" description="New meetings will appear as soon as they are recorded." />}
      </Panel>
      <Panel title="New leads" subtitle="Recently assigned to you">
        {data.new_leads.length ? <div className="lead-list">{data.new_leads.map((account) => <article key={account.id}><div><strong>{account.name}</strong><span>{account.industry ?? titleCase(account.account_type)}</span></div><Badge tone={(account.lead_score ?? 0) >= 70 ? "gold" : "neutral"}>{account.lead_score ?? "—"}</Badge></article>)}</div> : <EmptyState title="No new assignments" description="Newly assigned accounts will show here." />}
      </Panel>
      <Panel title="Recent activity" subtitle="Your latest completed work" className="span-two">
        {data.recent_activity.length ? <div className="activity-list">{data.recent_activity.map((item) => <ActivityRow key={item.id} item={item} />)}</div> : <EmptyState title="No recent activity" description="Log a call, email or meeting to begin the timeline." />}
      </Panel>
    </div>}
    <Modal title="Log sales activity" description="Record the outcome and optionally schedule the next follow-up." open={activityOpen} onClose={() => setActivityOpen(false)}>
      <form className="record-form" onSubmit={(event) => {
        const value = submitObject(event);
        create.mutate({ ...value, started_at: new Date().toISOString(), next_action_at: value.next_action_at ? new Date(String(value.next_action_at)).toISOString() : undefined } as Partial<Activity>);
      }}>
        <label>Activity type<select name="activity_type" required defaultValue="call"><option value="call">Call</option><option value="email">Email</option><option value="linkedin">LinkedIn</option><option value="whatsapp">WhatsApp</option><option value="meeting">Meeting</option><option value="demo">Demo</option><option value="proposal">Proposal</option><option value="note">Note</option></select></label>
        <label>Account ID<input name="account_id" placeholder="Paste account ID" /></label>
        <label className="span-two">Outcome<input name="outcome" required placeholder="What happened?" /></label>
        <label className="span-two">Notes<textarea name="notes" rows={3} placeholder="Useful context for the team" /></label>
        <label>Next action<input name="next_action" placeholder="Call back, send proposal…" /></label>
        <label>Next follow-up<input name="next_action_at" type="datetime-local" /></label>
        {create.isError && <div className="form-error">{create.error.message}</div>}
        <FormActions saving={create.isPending} onCancel={() => setActivityOpen(false)} />
      </form>
    </Modal>
  </div>;
}
