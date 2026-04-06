from pyspark.sql import SparkSession
from pyspark.sql.functions import col, to_date, avg, max, min, count, date_format
import matplotlib.pyplot as plt
import os
import pandas as pd # Used for plotting collected data

# Ensure output directory exists
OUTPUT_DIR = 'output_plots'
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

def analyze_data():
    print("Initializing Spark Session...")
    spark = SparkSession.builder \
        .appName("AppleHealthAnalysis") \
        .getOrCreate()
    
    # Silence logs
    spark.sparkContext.setLogLevel("ERROR")

    print("Reading data...")
    records_df = spark.read.csv("health_records.csv", header=True, inferSchema=True)
    workouts_df = spark.read.csv("workouts.csv", header=True, inferSchema=True)

    # 1. Heart Rate Analysis
    print("Analyzing Heart Rate...")
    hr_df = records_df.filter(col("type") == "HKQuantityTypeIdentifierHeartRate")
    hr_df = hr_df.withColumn("date", to_date(col("startDate"))) # Extract date part
    
    # Daily Average Heart Rate
    daily_hr = hr_df.groupBy("date").agg(avg("value").alias("avg_heart_rate")).orderBy("date")
    
    # Collect to Pandas for plotting (assuming data size fits in memory after aggregation)
    daily_hr_pd = daily_hr.toPandas()
    
    # Plotting Heart Rate
    plt.figure(figsize=(12, 6))
    plt.plot(daily_hr_pd['date'], daily_hr_pd['avg_heart_rate'], label='Daily Avg Heart Rate', color='red', alpha=0.7)
    plt.title('Daily Average Heart Rate')
    plt.xlabel('Date')
    plt.ylabel('BPM')
    plt.legend()
    plt.grid(True)
    plt.savefig(os.path.join(OUTPUT_DIR, 'heart_rate_trend.png'))
    plt.close()
    print(f"Saved heart_rate_trend.png to {OUTPUT_DIR}")

    # 2. Body Mass Analysis
    print("Analyzing Body Mass...")
    weight_df = records_df.filter(col("type") == "HKQuantityTypeIdentifierBodyMass")
    weight_df = weight_df.withColumn("date", to_date(col("startDate")))
    
    # Daily Weight (taking average if multiple entries per day)
    daily_weight = weight_df.groupBy("date").agg(avg("value").alias("weight_kg")).orderBy("date")
    
    daily_weight_pd = daily_weight.toPandas()
    
    # Plotting Weight
    plt.figure(figsize=(12, 6))
    plt.plot(daily_weight_pd['date'], daily_weight_pd['weight_kg'], label='Weight (kg)', color='blue', marker='o')
    plt.title('Body Mass Trend')
    plt.xlabel('Date')
    plt.ylabel('Weight (kg)')
    plt.legend()
    plt.grid(True)
    plt.savefig(os.path.join(OUTPUT_DIR, 'weight_trend.png'))
    plt.close()
    print(f"Saved weight_trend.png to {OUTPUT_DIR}")

    # 3. Workout Analysis
    print("Analyzing Workouts...")
    if workouts_df.count() > 0:
        workouts_df.createOrReplaceTempView("workouts")
        
        # Count by activity type
        workout_counts = spark.sql("""
            SELECT workoutActivityType, count(*) as count, avg(duration) as avg_duration, sum(totalDistance) as total_distance
            FROM workouts
            GROUP BY workoutActivityType
            ORDER BY count DESC
        """)
        
        workout_counts.show(truncate=False)
        
        workout_counts_pd = workout_counts.toPandas()
        
        # Plotting Workout Distribution
        plt.figure(figsize=(10, 6))
        # Remove prefix if present usually 'HKWorkoutActivityType'
        labels = [x.replace('HKWorkoutActivityType', '') for x in workout_counts_pd['workoutActivityType']]
        plt.bar(labels, workout_counts_pd['count'], color='green')
        plt.title('Workout Frequency by Type')
        plt.xlabel('Activity Type')
        plt.ylabel('Count')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        plt.savefig(os.path.join(OUTPUT_DIR, 'workout_distribution.png'))
        plt.close()
        print(f"Saved workout_distribution.png to {OUTPUT_DIR}")
    else:
        print("No workout data found.")

    spark.stop()
    print("Analysis Complete.")

if __name__ == "__main__":
    analyze_data()
