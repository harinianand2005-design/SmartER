import { Bar, BarChart, CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { AnalyticsResponse } from "../services/api";

export function ForecastChart({ forecasts }: { forecasts: Record<string, number> }) {
  const data = Object.entries(forecasts).map(([horizon, value]) => ({ horizon, arrivals: Number(value.toFixed(1)) }));
  return <div className="chart-box"><ResponsiveContainer width="100%" height={280}><LineChart data={data}><CartesianGrid strokeDasharray="3 3" stroke="#d9e2ec" /><XAxis dataKey="horizon" /><YAxis /><Tooltip /><Legend /><Line type="monotone" dataKey="arrivals" name="Expected arrivals" stroke="#147d92" strokeWidth={3} dot={{ r: 4 }} /></LineChart></ResponsiveContainer></div>;
}

export function ResourceChart({ resources }: { resources: { required_beds: number; required_doctors: number; required_nurses: number } }) {
  const data = [{ resource: "Beds", required: resources.required_beds }, { resource: "Doctors", required: resources.required_doctors }, { resource: "Nurses", required: resources.required_nurses }];
  return <div className="chart-box"><ResponsiveContainer width="100%" height={280}><BarChart data={data}><CartesianGrid strokeDasharray="3 3" stroke="#d9e2ec" /><XAxis dataKey="resource" /><YAxis /><Tooltip /><Bar dataKey="required" name="Required" fill="#ef8354" radius={[4, 4, 0, 0]} /></BarChart></ResponsiveContainer></div>;
}

export function ObservedArrivalsChart({ data }: { data: AnalyticsResponse["observed_metrics"] }) {
  return <div className="chart-box"><ResponsiveContainer width="100%" height={260}><LineChart data={data}><CartesianGrid strokeDasharray="3 3" stroke="#d9e2ec" /><XAxis dataKey="timestamp" tickFormatter={(value: string) => new Date(value).toLocaleDateString()} minTickGap={30} /><YAxis /><Tooltip labelFormatter={(value) => new Date(String(value)).toLocaleString()} /><Legend /><Line type="monotone" dataKey="arrivals" name="Observed arrivals" stroke="#147d92" strokeWidth={2} dot={false} /></LineChart></ResponsiveContainer></div>;
}

export function ObservedWaitingOccupancyChart({ data }: { data: AnalyticsResponse["observed_metrics"] }) {
  return <div className="chart-box"><ResponsiveContainer width="100%" height={260}><LineChart data={data}><CartesianGrid strokeDasharray="3 3" stroke="#d9e2ec" /><XAxis dataKey="timestamp" tickFormatter={(value: string) => new Date(value).toLocaleDateString()} minTickGap={30} /><YAxis yAxisId="wait" /><YAxis yAxisId="occupancy" orientation="right" domain={[0, 100]} /><Tooltip labelFormatter={(value) => new Date(String(value)).toLocaleString()} /><Legend /><Line yAxisId="wait" type="monotone" dataKey="average_wait_minutes" name="Waiting time (min)" stroke="#ef8354" strokeWidth={2} dot={false} /><Line yAxisId="occupancy" type="monotone" dataKey="occupancy_percentage" name="Occupancy (%)" stroke="#2680c2" strokeWidth={2} dot={false} /></LineChart></ResponsiveContainer></div>;
}

export function ResourceHistoryChart({ data }: { data: AnalyticsResponse["resource_history"] }) {
  return <div className="chart-box"><ResponsiveContainer width="100%" height={260}><LineChart data={data}><CartesianGrid strokeDasharray="3 3" stroke="#d9e2ec" /><XAxis dataKey="target_timestamp" tickFormatter={(value: string) => new Date(value).toLocaleDateString()} minTickGap={30} /><YAxis /><Tooltip labelFormatter={(value) => new Date(String(value)).toLocaleString()} /><Legend /><Line type="monotone" dataKey="required_beds" name="Predicted beds" stroke="#147d92" strokeWidth={2} dot={false} /><Line type="monotone" dataKey="required_doctors" name="Predicted doctors" stroke="#ef8354" strokeWidth={2} dot={false} /><Line type="monotone" dataKey="required_nurses" name="Predicted nurses" stroke="#2680c2" strokeWidth={2} dot={false} /></LineChart></ResponsiveContainer></div>;
}