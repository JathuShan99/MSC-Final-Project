import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go


class DashboardCharts:
    """
    Handles chart generation and visualization for the dashboard.
    """

    @staticmethod
    def daily_attendance_chart(daily_df):
        """
        Create daily attendance line chart.
        
        Args:
            daily_df: DataFrame with 'date' and 'count' columns
            
        Returns:
            Plotly figure
        """
        if daily_df.empty:
            return None
        
        fig = px.line(
            daily_df,
            x='date',
            y='count',
            title='Daily Attendance Trend',
            labels={'date': 'Date', 'count': 'Attendance Count'},
            markers=True
        )
        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="Attendance Count",
            hovermode='x unified'
        )
        return fig

    @staticmethod
    def weekly_attendance_chart(weekly_df):
        """
        Create weekly attendance bar chart.
        
        Args:
            weekly_df: DataFrame with 'week' and 'count' columns
            
        Returns:
            Plotly figure
        """
        if weekly_df.empty:
            return None
        
        fig = px.bar(
            weekly_df,
            x='week',
            y='count',
            title='Weekly Attendance Summary',
            labels={'week': 'Week', 'count': 'Attendance Count'}
        )
        fig.update_layout(
            xaxis_title="Week",
            yaxis_title="Attendance Count",
            xaxis_tickangle=-45
        )
        return fig

    @staticmethod
    def user_attendance_chart(user_df, max_users=20):
        """
        Create user attendance bar chart.
        
        Args:
            user_df: DataFrame with user attendance data
            max_users: Maximum number of users to display
            
        Returns:
            Plotly figure
        """
        if user_df.empty:
            return None
        
        # Limit to top N users
        display_df = user_df.head(max_users).copy()
        
        # Create display label
        display_df['label'] = display_df.apply(
            lambda row: f"{row['user_id']}\n({row.get('name', 'N/A')})",
            axis=1
        )
        
        fig = px.bar(
            display_df,
            x='label',
            y='attendance_count',
            title=f'Attendance per User (Top {min(max_users, len(user_df))})',
            labels={'label': 'User', 'attendance_count': 'Attendance Count'},
            color='attendance_count',
            color_continuous_scale='Blues'
        )
        fig.update_layout(
            xaxis_title="User",
            yaxis_title="Attendance Count",
            xaxis_tickangle=-45,
            showlegend=False
        )
        return fig

    @staticmethod
    def hourly_distribution_chart(hourly_df):
        """
        Create hourly attendance distribution chart.
        
        Args:
            hourly_df: DataFrame with 'hour' and 'count' columns
            
        Returns:
            Plotly figure
        """
        if hourly_df.empty:
            return None
        
        fig = px.bar(
            hourly_df,
            x='hour',
            y='count',
            title='Attendance Distribution by Hour of Day',
            labels={'hour': 'Hour of Day', 'count': 'Attendance Count'},
            color='count',
            color_continuous_scale='Viridis'
        )
        fig.update_layout(
            xaxis_title="Hour of Day (24-hour format)",
            yaxis_title="Attendance Count",
            xaxis=dict(tickmode='linear', tick0=0, dtick=1),
            showlegend=False
        )
        return fig

    @staticmethod
    def verification_stats_chart(stats):
        """
        Create verification statistics pie chart.
        
        Args:
            stats: Dictionary with verification statistics
            
        Returns:
            Plotly figure
        """
        if stats['total_records'] == 0:
            return None
        
        labels = ['Face Verified', 'Liveness Verified', 'Multi-Factor Verified', 'Not Verified']
        values = [
            stats['face_verified'],
            stats['liveness_verified'],
            stats['multi_factor_verified'],
            stats['total_records'] - stats['multi_factor_verified']
        ]
        
        # Filter out zero values for cleaner chart
        filtered_data = [(label, val) for label, val in zip(labels, values) if val > 0]
        if not filtered_data:
            return None
        
        labels, values = zip(*filtered_data)
        
        fig = px.pie(
            values=values,
            names=labels,
            title='Verification Statistics',
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        return fig

    @staticmethod
    def recognition_score_distribution(attendance_df):
        """
        Create recognition score distribution histogram.
        
        Args:
            attendance_df: DataFrame with attendance records including 'recognition_score'
            
        Returns:
            Plotly figure
        """
        if attendance_df.empty or 'recognition_score' not in attendance_df.columns:
            return None
        
        scores = attendance_df['recognition_score'].dropna()
        
        if scores.empty:
            return None
        
        fig = px.histogram(
            x=scores,
            title='Recognition Score Distribution',
            labels={'x': 'Recognition Score', 'y': 'Frequency'},
            nbins=20
        )
        fig.update_layout(
            xaxis_title="Recognition Score",
            yaxis_title="Frequency"
        )
        return fig

    @staticmethod
    def weekly_heatmap_chart(attendance_df):
        """
        Create weekly attendance heatmap (day of week × hour of day).
        
        Args:
            attendance_df: DataFrame with attendance records including 'timestamp'
            
        Returns:
            Plotly figure
        """
        if attendance_df.empty or 'timestamp' not in attendance_df.columns:
            return None
        
        df = attendance_df.copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df['day_of_week'] = df['timestamp'].dt.day_name()
        df['hour'] = df['timestamp'].dt.hour
        
        # Create pivot table
        day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        heatmap_data = df.groupby(['day_of_week', 'hour']).size().reset_index(name='count')
        
        # Create pivot
        pivot = heatmap_data.pivot(index='day_of_week', columns='hour', values='count').fillna(0)
        
        # Reorder days
        pivot = pivot.reindex([day for day in day_order if day in pivot.index])
        
        fig = px.imshow(
            pivot.values,
            labels=dict(x="Hour of Day", y="Day of Week", color="Attendance Count"),
            x=[f"{h:02d}:00" for h in pivot.columns],
            y=pivot.index,
            title='Weekly Attendance Heatmap',
            color_continuous_scale='YlOrRd',
            aspect="auto"
        )
        fig.update_layout(
            xaxis_title="Hour of Day",
            yaxis_title="Day of Week"
        )
        return fig

    @staticmethod
    def multi_factor_funnel_chart(attendance_df):
        """
        Create multi-factor verification funnel chart.
        
        Args:
            attendance_df: DataFrame with attendance records
            
        Returns:
            Plotly figure
        """
        if attendance_df.empty:
            return None
        
        # Calculate funnel stages
        total_records = len(attendance_df)
        
        face_detected = total_records  # All records have face detection
        face_verified = int(attendance_df['face_verified'].sum()) if 'face_verified' in attendance_df.columns else 0
        liveness_verified = int(attendance_df['liveness_verified'].sum()) if 'liveness_verified' in attendance_df.columns else 0
        multi_factor = int(((attendance_df['face_verified'] == 1) & (attendance_df['liveness_verified'] == 1)).sum()) if 'face_verified' in attendance_df.columns and 'liveness_verified' in attendance_df.columns else 0
        
        stages = ['Face Detected', 'Face Verified', 'Liveness Verified', 'Multi-Factor Passed']
        values = [face_detected, face_verified, liveness_verified, multi_factor]
        
        fig = go.Figure(go.Funnel(
            y=stages,
            x=values,
            textposition="inside",
            textinfo="value+percent initial",
            marker={"color": ["deepskyblue", "lightsalmon", "tan", "teal"]}
        ))
        fig.update_layout(
            title="Multi-Factor Verification Funnel",
            height=400
        )
        return fig

    @staticmethod
    def liveness_failure_rate_chart(attendance_df, group_by='date'):
        """
        Create liveness failure rate over time chart.
        
        Args:
            attendance_df: DataFrame with attendance records
            group_by: 'date' or 'week' for grouping
            
        Returns:
            Plotly figure
        """
        if attendance_df.empty or 'liveness_verified' not in attendance_df.columns:
            return None
        
        df = attendance_df.copy()
        
        if 'timestamp' not in df.columns:
            return None
        
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        if group_by == 'date':
            df['group'] = df['timestamp'].dt.date
        elif group_by == 'week':
            df['group'] = df['timestamp'].dt.to_period('W').astype(str)
        else:
            df['group'] = df['timestamp'].dt.date
        
        # Calculate failure rate per group
        grouped = df.groupby('group').agg({
            'liveness_verified': ['sum', 'count']
        }).reset_index()
        grouped.columns = ['group', 'liveness_passed', 'total']
        grouped['liveness_failed'] = grouped['total'] - grouped['liveness_passed']
        grouped['failure_rate'] = (grouped['liveness_failed'] / grouped['total'] * 100).round(2)
        
        grouped = grouped.sort_values('group')
        
        fig = px.line(
            grouped,
            x='group',
            y='failure_rate',
            title='Liveness Failure Rate Over Time',
            labels={'group': 'Date' if group_by == 'date' else 'Week', 'failure_rate': 'Failure Rate (%)'},
            markers=True
        )
        fig.update_layout(
            xaxis_title="Date" if group_by == 'date' else "Week",
            yaxis_title="Failure Rate (%)",
            hovermode='x unified'
        )
        fig.update_traces(line_color='red', line_width=2)
        return fig

