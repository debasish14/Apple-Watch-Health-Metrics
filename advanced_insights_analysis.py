from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col, to_date, to_timestamp, avg, max, min, count, stddev, 
    hour, dayofweek, month, weekofyear, date_format, 
    sum as spark_sum, when, lag, lead, datediff, percentile_approx,
    year, corr, window
)
from pyspark.sql.window import Window
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import os
from datetime import datetime

# Set style for better visualizations
sns.set_style('darkgrid')
plt.rcParams['figure.figsize'] = (14, 8)

OUTPUT_DIR = 'output_plots'
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def analyze_advanced_insights():
    print("🚀 Starting Advanced Apple Watch Data Analysis...")
    print("=" * 70)
    
    spark = SparkSession.builder \
        .appName("AdvancedAppleHealthInsights") \
        .config("spark.driver.memory", "4g") \
        .getOrCreate()
    
    spark.sparkContext.setLogLevel("ERROR")
    
    print("📊 Loading data...")
    records_df = spark.read.csv("health_records.csv", header=True, inferSchema=True)
    workouts_df = spark.read.csv("workouts.csv", header=True, inferSchema=True)
    
    # Convert timestamps
    records_df = records_df.withColumn("start_ts", to_timestamp(col("startDate")))
    records_df = records_df.withColumn("date", to_date(col("startDate")))
    records_df = records_df.withColumn("hour", hour(col("start_ts")))
    records_df = records_df.withColumn("day_of_week", dayofweek(col("start_ts")))
    records_df = records_df.withColumn("month", month(col("start_ts")))
    records_df = records_df.withColumn("year", year(col("start_ts")))
    
    # Cache for performance
    records_df.cache()
    
    print("\n" + "=" * 70)
    insights = []
    
    # ========== INSIGHT 1: Circadian Rhythm Analysis ==========
    print("\n🌙 INSIGHT 1: Analyzing Your Circadian Rhythm Patterns...")
    hr_df = records_df.filter(col("type") == "HKQuantityTypeIdentifierHeartRate")
    
    hourly_hr = hr_df.groupBy("hour").agg(
        avg("value").alias("avg_hr"),
        stddev("value").alias("std_hr"),
        count("value").alias("count")
    ).orderBy("hour")
    
    hourly_hr_pd = hourly_hr.toPandas()
    
    fig, ax = plt.subplots(figsize=(15, 6))
    ax.plot(hourly_hr_pd['hour'], hourly_hr_pd['avg_hr'], 
            marker='o', linewidth=2, markersize=8, color='#FF6B6B')
    ax.fill_between(hourly_hr_pd['hour'], 
                     hourly_hr_pd['avg_hr'] - hourly_hr_pd['std_hr'],
                     hourly_hr_pd['avg_hr'] + hourly_hr_pd['std_hr'],
                     alpha=0.3, color='#FF6B6B')
    ax.set_xlabel('Hour of Day', fontsize=12, fontweight='bold')
    ax.set_ylabel('Heart Rate (BPM)', fontsize=12, fontweight='bold')
    ax.set_title('Your Circadian Heart Rate Rhythm (24-Hour Pattern)', 
                 fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'circadian_rhythm.png'), dpi=300)
    plt.close()
    
    # Find peak and trough times
    peak_hour = hourly_hr_pd.loc[hourly_hr_pd['avg_hr'].idxmax(), 'hour']
    trough_hour = hourly_hr_pd.loc[hourly_hr_pd['avg_hr'].idxmin(), 'hour']
    insights.append(f"⏰ Your heart rate peaks at {int(peak_hour):02d}:00 and is lowest at {int(trough_hour):02d}:00")
    
    # ========== INSIGHT 2: Weekly Activity Patterns ==========
    print("📅 INSIGHT 2: Discovering Weekly Activity Patterns...")
    
    steps_df = records_df.filter(col("type") == "HKQuantityTypeIdentifierStepCount")
    daily_steps = steps_df.groupBy("date", "day_of_week").agg(
        spark_sum("value").alias("total_steps")
    )
    
    weekly_pattern = daily_steps.groupBy("day_of_week").agg(
        avg("total_steps").alias("avg_steps"),
        stddev("total_steps").alias("std_steps")
    ).orderBy("day_of_week")
    
    weekly_pd = weekly_pattern.toPandas()
    days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
    
    fig, ax = plt.subplots(figsize=(12, 6))
    bars = ax.bar(range(7), weekly_pd['avg_steps'], 
                  color=['#FF6B6B' if i in [0, 6] else '#4ECDC4' for i in range(7)],
                  alpha=0.8, edgecolor='black', linewidth=1.5)
    ax.errorbar(range(7), weekly_pd['avg_steps'], yerr=weekly_pd['std_steps'],
                fmt='none', ecolor='black', capsize=5, alpha=0.5)
    ax.set_xticks(range(7))
    ax.set_xticklabels(days, fontweight='bold')
    ax.set_ylabel('Average Steps', fontsize=12, fontweight='bold')
    ax.set_title('Weekly Activity Pattern: When Are You Most Active?', 
                 fontsize=14, fontweight='bold')
    ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    plt.savefig(os.path.join(OUTPUT_DIR, 'weekly_activity_pattern.png'), dpi=300)
    plt.close()
    
    most_active_day = days[weekly_pd['avg_steps'].idxmax()]
    least_active_day = days[weekly_pd['avg_steps'].idxmin()]
    insights.append(f"🏃 You're most active on {most_active_day}s and least active on {least_active_day}s")
    
    # ========== INSIGHT 3: Sleep Quality Analysis ==========
    print("😴 INSIGHT 3: Analyzing Sleep Patterns...")
    
    sleep_df = records_df.filter(col("type") == "HKCategoryTypeIdentifierSleepAnalysis")
    
    if sleep_df.count() > 0:
        sleep_df = sleep_df.withColumn("start_ts", to_timestamp(col("startDate")))
        sleep_df = sleep_df.withColumn("end_ts", to_timestamp(col("endDate")))
        sleep_df = sleep_df.withColumn("duration_hours", 
                                       (col("end_ts").cast("long") - col("start_ts").cast("long")) / 3600)
        
        daily_sleep = sleep_df.groupBy("date").agg(
            spark_sum("duration_hours").alias("total_sleep_hours")
        ).orderBy("date")
        
        sleep_pd = daily_sleep.toPandas()
        
        if len(sleep_pd) > 0:
            fig, ax = plt.subplots(figsize=(14, 6))
            ax.plot(sleep_pd['date'], sleep_pd['total_sleep_hours'], 
                   color='#9B59B6', alpha=0.7, linewidth=1.5)
            ax.axhline(y=7, color='green', linestyle='--', label='Recommended (7h)', linewidth=2)
            ax.fill_between(sleep_pd['date'], sleep_pd['total_sleep_hours'], 
                           alpha=0.3, color='#9B59B6')
            ax.set_xlabel('Date', fontsize=12, fontweight='bold')
            ax.set_ylabel('Sleep Duration (hours)', fontsize=12, fontweight='bold')
            ax.set_title('Sleep Duration Trends', fontsize=14, fontweight='bold')
            ax.legend()
            ax.grid(True, alpha=0.3)
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(os.path.join(OUTPUT_DIR, 'sleep_analysis.png'), dpi=300)
            plt.close()
            
            avg_sleep = sleep_pd['total_sleep_hours'].mean()
            insights.append(f"💤 Your average sleep duration: {avg_sleep:.1f} hours/night")
    
    # ========== INSIGHT 4: Heart Rate Variability (Stress Indicator) ==========
    print("💓 INSIGHT 4: Heart Rate Variability Analysis (Stress & Recovery)...")
    
    hrv_df = records_df.filter(col("type") == "HKQuantityTypeIdentifierHeartRateVariabilitySDNN")
    
    if hrv_df.count() > 0:
        daily_hrv = hrv_df.groupBy("date").agg(
            avg("value").alias("avg_hrv")
        ).orderBy("date")
        
        hrv_pd = daily_hrv.toPandas()
        
        fig, ax = plt.subplots(figsize=(14, 6))
        ax.plot(hrv_pd['date'], hrv_pd['avg_hrv'], color='#E74C3C', linewidth=2)
        ax.fill_between(hrv_pd['date'], hrv_pd['avg_hrv'], alpha=0.3, color='#E74C3C')
        ax.set_xlabel('Date', fontsize=12, fontweight='bold')
        ax.set_ylabel('HRV (ms)', fontsize=12, fontweight='bold')
        ax.set_title('Heart Rate Variability: Your Stress & Recovery Indicator', 
                     fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, 'hrv_analysis.png'), dpi=300)
        plt.close()
        
        avg_hrv = hrv_pd['avg_hrv'].mean()
        insights.append(f"📈 Average HRV: {avg_hrv:.1f}ms (Higher = Better recovery)")
    
    # ========== INSIGHT 5: Walking Steadiness & Fall Risk ==========
    print("🚶 INSIGHT 5: Walking Steadiness Analysis...")
    
    steadiness_df = records_df.filter(col("type") == "HKQuantityTypeIdentifierAppleWalkingSteadiness")
    
    if steadiness_df.count() > 0:
        steadiness_trend = steadiness_df.groupBy("date").agg(
            avg("value").alias("steadiness")
        ).orderBy("date")
        
        steadiness_pd = steadiness_trend.toPandas()
        
        fig, ax = plt.subplots(figsize=(14, 6))
        ax.plot(steadiness_pd['date'], steadiness_pd['steadiness'] * 100, 
               color='#3498DB', linewidth=2, marker='o')
        ax.set_xlabel('Date', fontsize=12, fontweight='bold')
        ax.set_ylabel('Walking Steadiness (%)', fontsize=12, fontweight='bold')
        ax.set_title('Walking Steadiness Over Time', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, 'walking_steadiness.png'), dpi=300)
        plt.close()
        
        avg_steadiness = steadiness_pd['steadiness'].mean() * 100
        insights.append(f"🚶 Average walking steadiness: {avg_steadiness:.1f}%")
    
    # ========== INSIGHT 6: VO2 Max Fitness Trend ==========
    print("🏋️ INSIGHT 6: Cardio Fitness (VO2 Max) Trends...")
    
    vo2_df = records_df.filter(col("type") == "HKQuantityTypeIdentifierVO2Max")
    
    if vo2_df.count() > 0:
        vo2_trend = vo2_df.groupBy("date").agg(
            avg("value").alias("vo2max")
        ).orderBy("date")
        
        vo2_pd = vo2_trend.toPandas()
        
        fig, ax = plt.subplots(figsize=(14, 6))
        ax.plot(vo2_pd['date'], vo2_pd['vo2max'], 
               color='#2ECC71', linewidth=2, marker='o')
        ax.set_xlabel('Date', fontsize=12, fontweight='bold')
        ax.set_ylabel('VO2 Max (ml/kg/min)', fontsize=12, fontweight='bold')
        ax.set_title('Cardio Fitness Level Over Time', fontsize=14, fontweight='bold')
        ax.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, 'vo2max_trend.png'), dpi=300)
        plt.close()
        
        latest_vo2 = vo2_pd['vo2max'].iloc[-1]
        insights.append(f"💪 Latest VO2 Max: {latest_vo2:.1f} ml/kg/min")
    
    # ========== INSIGHT 7: Audio Exposure & Hearing Health ==========
    print("🎧 INSIGHT 7: Headphone Audio Exposure Analysis...")
    
    audio_df = records_df.filter(col("type") == "HKQuantityTypeIdentifierHeadphoneAudioExposure")
    
    if audio_df.count() > 0:
        daily_audio = audio_df.groupBy("date").agg(
            avg("value").alias("avg_exposure"),
            max("value").alias("max_exposure")
        ).orderBy("date")
        
        audio_pd = daily_audio.toPandas()
        
        fig, ax = plt.subplots(figsize=(14, 6))
        ax.plot(audio_pd['date'], audio_pd['avg_exposure'], 
               color='#F39C12', label='Average', linewidth=2)
        ax.axhline(y=80, color='red', linestyle='--', 
                  label='Safe Limit (80 dB)', linewidth=2)
        ax.set_xlabel('Date', fontsize=12, fontweight='bold')
        ax.set_ylabel('Audio Exposure (dB)', fontsize=12, fontweight='bold')
        ax.set_title('Headphone Audio Exposure: Protecting Your Hearing', 
                     fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, 'audio_exposure.png'), dpi=300)
        plt.close()
        
        avg_exposure = audio_pd['avg_exposure'].mean()
        days_over_limit = len(audio_pd[audio_pd['avg_exposure'] > 80])
        insights.append(f"🎧 Average audio exposure: {avg_exposure:.1f} dB ({days_over_limit} days exceeded safe limit)")
    
    # ========== INSIGHT 8: Time in Daylight (Circadian Health) ==========
    print("☀️ INSIGHT 8: Daylight Exposure Analysis...")
    
    daylight_df = records_df.filter(col("type") == "HKQuantityTypeIdentifierTimeInDaylight")
    
    if daylight_df.count() > 0:
        daily_daylight = daylight_df.groupBy("date").agg(
            spark_sum("value").alias("minutes_daylight")
        ).orderBy("date")
        
        daylight_pd = daily_daylight.toPandas()
        daylight_pd['hours_daylight'] = daylight_pd['minutes_daylight'] / 60
        
        fig, ax = plt.subplots(figsize=(14, 6))
        ax.bar(daylight_pd['date'], daylight_pd['hours_daylight'], 
              color='#F1C40F', alpha=0.8, edgecolor='black')
        ax.axhline(y=2, color='green', linestyle='--', 
                  label='Recommended (2h)', linewidth=2)
        ax.set_xlabel('Date', fontsize=12, fontweight='bold')
        ax.set_ylabel('Time in Daylight (hours)', fontsize=12, fontweight='bold')
        ax.set_title('Daily Daylight Exposure: Are You Getting Enough Sun?', 
                     fontsize=14, fontweight='bold')
        ax.legend()
        ax.grid(axis='y', alpha=0.3)
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, 'daylight_exposure.png'), dpi=300)
        plt.close()
        
        avg_daylight = daylight_pd['hours_daylight'].mean()
        insights.append(f"☀️ Average daily daylight: {avg_daylight:.1f} hours")
    
    # ========== INSIGHT 9: Resting Heart Rate Trend (Fitness Indicator) ==========
    print("❤️ INSIGHT 9: Resting Heart Rate - Long-term Fitness Indicator...")
    
    rhr_df = records_df.filter(col("type") == "HKQuantityTypeIdentifierRestingHeartRate")
    
    if rhr_df.count() > 0:
        daily_rhr = rhr_df.groupBy("date").agg(
            avg("value").alias("resting_hr")
        ).orderBy("date")
        
        rhr_pd = daily_rhr.toPandas()
        
        # Calculate trend
        if len(rhr_pd) > 1:
            z = np.polyfit(range(len(rhr_pd)), rhr_pd['resting_hr'], 1)
            p = np.poly1d(z)
            
            fig, ax = plt.subplots(figsize=(14, 6))
            ax.plot(rhr_pd['date'], rhr_pd['resting_hr'], 
                   color='#E74C3C', linewidth=2, label='Actual')
            ax.plot(rhr_pd['date'], p(range(len(rhr_pd))), 
                   color='#2ECC71', linestyle='--', linewidth=2, label='Trend')
            ax.set_xlabel('Date', fontsize=12, fontweight='bold')
            ax.set_ylabel('Resting Heart Rate (BPM)', fontsize=12, fontweight='bold')
            ax.set_title('Resting Heart Rate: Your Fitness Trajectory', 
                         fontsize=14, fontweight='bold')
            ax.legend()
            ax.grid(True, alpha=0.3)
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(os.path.join(OUTPUT_DIR, 'resting_hr_trend.png'), dpi=300)
            plt.close()
            
            trend_direction = "decreasing 📉" if z[0] < 0 else "increasing 📈"
            insights.append(f"❤️ Resting HR trend: {trend_direction} (Lower is better for fitness)")
    
    # ========== INSIGHT 10: Mindfulness Practice ==========
    print("🧘 INSIGHT 10: Mindfulness & Mental Health Tracking...")
    
    mindful_df = records_df.filter(col("type") == "HKCategoryTypeIdentifierMindfulSession")
    
    if mindful_df.count() > 0:
        mindful_df = mindful_df.withColumn("start_ts", to_timestamp(col("startDate")))
        mindful_df = mindful_df.withColumn("end_ts", to_timestamp(col("endDate")))
        mindful_df = mindful_df.withColumn("duration_min", 
                                          (col("end_ts").cast("long") - col("start_ts").cast("long")) / 60)
        
        monthly_mindful = mindful_df.groupBy(year("date").alias("year"), 
                                             month("date").alias("month")).agg(
            count("*").alias("sessions"),
            spark_sum("duration_min").alias("total_minutes")
        ).orderBy("year", "month")
        
        mindful_pd = monthly_mindful.toPandas()
        mindful_pd['month_label'] = mindful_pd.apply(
            lambda x: f"{int(x['year'])}-{int(x['month']):02d}", axis=1
        )
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10))
        
        ax1.bar(mindful_pd['month_label'], mindful_pd['sessions'], 
               color='#9B59B6', alpha=0.8)
        ax1.set_ylabel('Number of Sessions', fontsize=12, fontweight='bold')
        ax1.set_title('Monthly Mindfulness Sessions', fontsize=12, fontweight='bold')
        ax1.grid(axis='y', alpha=0.3)
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
        
        ax2.bar(mindful_pd['month_label'], mindful_pd['total_minutes'], 
               color='#3498DB', alpha=0.8)
        ax2.set_ylabel('Total Minutes', fontsize=12, fontweight='bold')
        ax2.set_xlabel('Month', fontsize=12, fontweight='bold')
        ax2.set_title('Monthly Mindfulness Time', fontsize=12, fontweight='bold')
        ax2.grid(axis='y', alpha=0.3)
        plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45)
        
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, 'mindfulness_practice.png'), dpi=300)
        plt.close()
        
        total_sessions = mindful_pd['sessions'].sum()
        insights.append(f"🧘 Total mindfulness sessions: {total_sessions}")
    
    # ========== SUMMARY DASHBOARD ==========
    print("\n" + "=" * 70)
    print("📝 GENERATING COMPREHENSIVE INSIGHTS SUMMARY...")
    print("=" * 70)
    
    for i, insight in enumerate(insights, 1):
        print(f"{i}. {insight}")
    
    # Save insights to file
    with open(os.path.join(OUTPUT_DIR, 'insights_summary.txt'), 'w') as f:
        f.write("UNIQUE INSIGHTS FROM YOUR APPLE WATCH DATA\n")
        f.write("=" * 70 + "\n\n")
        for i, insight in enumerate(insights, 1):
            f.write(f"{i}. {insight}\n")
        f.write("\n" + "=" * 70 + "\n")
        f.write(f"Analysis completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    print(f"\n✅ Analysis complete! Check '{OUTPUT_DIR}' folder for all visualizations.")
    print(f"📄 Insights summary saved to: {os.path.join(OUTPUT_DIR, 'insights_summary.txt')}")
    
    spark.stop()

if __name__ == "__main__":
    analyze_advanced_insights()
