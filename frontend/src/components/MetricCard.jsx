import React from 'react';

const MetricCard = ({ title, value, subtext, icon: Icon }) => {
    return (
        <div className="bg-card text-card-foreground rounded-lg border shadow-sm p-6">
            <div className="flex flex-row items-center justify-between space-y-0 pb-2">
                <h3 className="tracking-tight text-sm font-medium text-muted-foreground">{title}</h3>
                {Icon && <Icon className="h-4 w-4 text-muted-foreground" />}
            </div>
            <div className="text-2xl font-bold">{value}</div>
            <p className="text-xs text-muted-foreground">{subtext}</p>
        </div>
    );
};

export default MetricCard;
