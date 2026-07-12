import React, { useMemo, useState } from 'react';

// GitHub's exact contribution palette (light / dark), levels 0-4.
const LEVEL_CLASSES = [
    'bg-[#ebedf0] dark:bg-[#161b22]',
    'bg-[#9be9a8] dark:bg-[#0e4429]',
    'bg-[#40c463] dark:bg-[#006d32]',
    'bg-[#30a14e] dark:bg-[#26a641]',
    'bg-[#216e39] dark:bg-[#39d353]',
];

const WEEKDAY_LABELS = { 1: 'Mon', 3: 'Wed', 5: 'Fri' };
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

const toKey = (d) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;

// Build GitHub's grid: columns are weeks, rows Sun..Sat.
// Cells outside [start, end] are null (rendered invisible).
function buildWeeks(start, end) {
    const gridStart = new Date(start);
    gridStart.setDate(gridStart.getDate() - gridStart.getDay()); // back to Sunday
    const weeks = [];
    for (let d = new Date(gridStart); d <= end; d.setDate(d.getDate() + 1)) {
        const week = Math.floor((d - gridStart) / (7 * 86400000));
        (weeks[week] ??= Array(7).fill(null))[d.getDay()] = d < start ? null : toKey(d);
    }
    return weeks;
}

// Label a week's column when the month changes relative to the previous week.
// A label whose month occupies fewer than 3 columns (a clipped first month)
// is suppressed so adjacent labels never overlap — same as GitHub.
function monthLabels(weeks) {
    let prev = -1;
    const labels = weeks.map((week) => {
        const first = week.find(Boolean);
        if (!first) return null;
        const month = Number(first.slice(5, 7)) - 1;
        if (month === prev) return null;
        prev = month;
        return MONTHS[month];
    });
    return labels.map((label, i) =>
        label && labels.slice(i + 1, i + 3).some(Boolean) ? null : label
    );
}

const ActivityCalendar = ({ data }) => {
    const [metric, setMetric] = useState('kcal'); // 'kcal' | 'steps'
    const [period, setPeriod] = useState('last-year');

    const byDate = useMemo(() => Object.fromEntries((data ?? []).map((d) => [d.date, d])), [data]);

    const years = useMemo(
        () => [...new Set((data ?? []).map((d) => d.date.slice(0, 4)))].sort().reverse(),
        [data]
    );

    const { weeks, labels, activeDays, periodName } = useMemo(() => {
        let start, end, name;
        if (period === 'last-year') {
            const last = data?.length ? data[data.length - 1].date : toKey(new Date());
            end = new Date(`${last}T00:00:00`);
            start = new Date(end);
            start.setDate(start.getDate() - 364);
            name = 'the last year';
        } else {
            start = new Date(`${period}-01-01T00:00:00`);
            end = new Date(`${period}-12-31T00:00:00`);
            name = period;
        }
        const weeks = buildWeeks(start, end);
        const levelKey = metric === 'kcal' ? 'level_kcal' : 'level_steps';
        const activeDays = weeks.flat().filter((key) => key && (byDate[key]?.[levelKey] ?? 0) > 0).length;
        return { weeks, labels: monthLabels(weeks), activeDays, periodName: name };
    }, [data, byDate, period, metric]);

    if (!data?.length) return null;

    const levelKey = metric === 'kcal' ? 'level_kcal' : 'level_steps';

    const tooltip = (key) => {
        const day = byDate[key];
        const nice = new Date(`${key}T00:00:00`).toLocaleDateString('en-US', {
            month: 'short', day: 'numeric', year: 'numeric',
        });
        if (!day) return `No activity on ${nice}`;
        const parts = [];
        if (day.steps) parts.push(`${Math.round(day.steps).toLocaleString()} steps`);
        if (day.active_kcal) parts.push(`${Math.round(day.active_kcal).toLocaleString()} kcal`);
        if (day.distance_km) parts.push(`${day.distance_km} km`);
        return `${parts.join(' · ') || 'No activity'} on ${nice}`;
    };

    return (
        <div className="bg-card text-card-foreground rounded-xl border shadow-sm">
            <div className="p-6 flex flex-col gap-1 sm:flex-row sm:items-center sm:justify-between">
                <div className="space-y-0.5">
                    <h3 className="font-semibold leading-none tracking-tight">
                        {activeDays} active days in {periodName}
                    </h3>
                    <p className="text-sm text-muted-foreground">
                        Daily {metric === 'kcal' ? 'active energy' : 'steps'}, shaded by your own quartiles
                    </p>
                </div>
                <div className="flex items-center gap-2">
                    <div className="flex rounded-md border text-xs">
                        {['kcal', 'steps'].map((m) => (
                            <button
                                key={m}
                                onClick={() => setMetric(m)}
                                className={`px-2.5 py-1 first:rounded-l-md last:rounded-r-md ${
                                    metric === m ? 'bg-primary text-primary-foreground' : 'hover:bg-muted'
                                }`}
                            >
                                {m === 'kcal' ? 'Energy' : 'Steps'}
                            </button>
                        ))}
                    </div>
                    <div className="flex rounded-md border text-xs">
                        {['last-year', ...years].map((p) => (
                            <button
                                key={p}
                                onClick={() => setPeriod(p)}
                                className={`px-2.5 py-1 first:rounded-l-md last:rounded-r-md ${
                                    period === p ? 'bg-primary text-primary-foreground' : 'hover:bg-muted'
                                }`}
                            >
                                {p === 'last-year' ? 'Last year' : p}
                            </button>
                        ))}
                    </div>
                </div>
            </div>

            <div className="px-6 pb-6 overflow-x-auto">
                <div className="inline-block">
                    {/* month labels */}
                    <div className="flex text-xs text-muted-foreground mb-1 ml-8">
                        {labels.map((label, i) => (
                            <div key={i} className="w-[14px] shrink-0">{label ?? ''}</div>
                        ))}
                    </div>
                    <div className="flex">
                        {/* weekday labels */}
                        <div className="flex flex-col mr-2 text-xs text-muted-foreground w-6 shrink-0">
                            {Array.from({ length: 7 }, (_, day) => (
                                <div key={day} className="h-[14px] leading-[11px]">
                                    {WEEKDAY_LABELS[day] ?? ''}
                                </div>
                            ))}
                        </div>
                        {/* the grid */}
                        {weeks.map((week, w) => (
                            <div key={w} className="flex flex-col w-[14px] shrink-0">
                                {week.map((key, day) =>
                                    key ? (
                                        <div
                                            key={day}
                                            title={tooltip(key)}
                                            className={`h-[11px] w-[11px] mb-[3px] rounded-[2px] ${
                                                LEVEL_CLASSES[byDate[key]?.[levelKey] ?? 0]
                                            }`}
                                        />
                                    ) : (
                                        <div key={day} className="h-[11px] w-[11px] mb-[3px]" />
                                    )
                                )}
                            </div>
                        ))}
                    </div>
                    {/* legend */}
                    <div className="flex items-center justify-end gap-1 mt-2 text-xs text-muted-foreground">
                        <span className="mr-1">Less</span>
                        {LEVEL_CLASSES.map((cls, i) => (
                            <div key={i} className={`h-[11px] w-[11px] rounded-[2px] ${cls}`} />
                        ))}
                        <span className="ml-1">More</span>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ActivityCalendar;
