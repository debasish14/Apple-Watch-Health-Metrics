import React, { useEffect, useState } from 'react';
import UploadZone from './UploadZone';
import MetricCard from './MetricCard';
import HeartRateChart from './HeartRateChart';
import WorkoutChart from './WorkoutChart';
import ThemeToggle from './ThemeToggle';
import { Activity, Heart, Scale, Flame } from 'lucide-react';

const Dashboard = () => {
    const [metrics, setMetrics] = useState(null);
    const [loading, setLoading] = useState(true);

    const fetchMetrics = async () => {
        setLoading(true);
        try {
            const res = await fetch('/api/health-metrics');
            if (res.ok) {
                const data = await res.json();
                setMetrics(data);
            }
        } catch (error) {
            console.error("Failed to fetch metrics", error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchMetrics();
    }, []);

    const handleUploadSuccess = () => {
        fetchMetrics();
    };

    if (loading && !metrics) {
        return <div className="flex h-screen items-center justify-center">Loading...</div>;
    }

    return (
        <div className="container mx-auto p-8 space-y-8">
            <header className="flex flex-col md:flex-row justify-between items-center gap-4">
                <div>
                    <h1 className="text-3xl font-bold tracking-tight">Health Data Insights</h1>
                    <p className="text-muted-foreground">Visualize your Apple Watch export data.</p>
                </div>
                <div className="w-full md:w-auto">
                    {/* Could put a small refresh button or date picker here */}
                </div>
            </header>

            <section>
                <UploadZone onUploadSuccess={handleUploadSuccess} />
            </section>

            {metrics && (
                <div className="space-y-8 fade-in">
                    {/* Summary Cards */}
                    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
                        <MetricCard
                            title="Total Workouts"
                            value={metrics.workouts ? metrics.workouts.reduce((acc, curr) => acc + curr.value, 0) : 0}
                            icon={Activity}
                            subtext="Recorded activities"
                        />
                        <MetricCard
                            title="Avg Heart Rate"
                            value={metrics.heartRate ? `${Math.round(metrics.heartRate.reduce((acc, c) => acc + c.value, 0) / metrics.heartRate.length)} BPM` : "--"}
                            icon={Heart}
                            subtext="Across all collected days"
                        />
                        <MetricCard
                            title="Current Weight"
                            value={metrics.weight && metrics.weight.length > 0 ? `${metrics.weight[metrics.weight.length - 1].value} kg` : "--"}
                            icon={Scale}
                            subtext="Most recent record"
                        />
                        <MetricCard
                            title="Calories Burned"
                            value="--"
                            icon={Flame}
                            subtext="Not yet implemented"
                        />
                    </div>

                    {/* Charts */}
                    <div className="grid gap-4 md:grid-cols-2">
                        <div className="bg-card text-card-foreground rounded-xl border shadow-sm col-span-2 lg:col-span-1">
                            <div className="p-6 flex flex-col space-y-0.5">
                                <h3 className="font-semibold leading-none tracking-tight">Heart Rate Trend</h3>
                                <p className="text-sm text-muted-foreground">Daily average heart rate over time</p>
                            </div>
                            <div className="p-6 pt-0">
                                <HeartRateChart data={metrics.heartRate} />
                            </div>
                        </div>

                        <div className="bg-card text-card-foreground rounded-xl border shadow-sm col-span-2 lg:col-span-1">
                            <div className="p-6 flex flex-col space-y-0.5">
                                <h3 className="font-semibold leading-none tracking-tight">Workout Distribution</h3>
                                <p className="text-sm text-muted-foreground">Count of activities by type</p>
                            </div>
                            <div className="p-6 pt-0">
                                <WorkoutChart data={metrics.workouts} />
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Dashboard;
