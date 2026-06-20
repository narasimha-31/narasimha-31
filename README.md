![gitartwork](gitartwork.svg)

<p align="center">
  <img width="100%" src="data-pipeline.svg" alt="Data pipeline: sources, Kafka, Airflow, dbt, Postgres"/>
</p>

<p align="center">
  <a href="https://www.linkedin.com/in/narasimha31/"><img src="https://img.shields.io/badge/LinkedIn-0A66C2?style=for-the-badge&logo=linkedin&logoColor=white"/></a>
  <a href="https://narasimharoyal.com/"><img src="https://img.shields.io/badge/Portfolio-24A99F?style=for-the-badge&logo=google-chrome&logoColor=white"/></a>
  <a href="mailto:narasimharoyal31@gmail.com"><img src="https://img.shields.io/badge/Email-EA4335?style=for-the-badge&logo=gmail&logoColor=white"/></a>
  <img src="https://komarev.com/ghpvc/?username=narasimha-31&label=Profile+views&color=24A99F&style=for-the-badge"/>
</p>

<img width="100%" src="https://capsule-render.vercel.app/api?type=rect&height=3&color=0:1ba1e3,50:9168cf,100:ec5f78&animation=twinkling"/>

## About Me

I'm a data engineer in Houston. I started out in analytics and moved into building the pipelines that sit behind the dashboards. Most of my day is Python and SQL: getting data out of messy sources and into clean, well modeled tables that people can actually query.

Lately I work mostly with Kafka, Airflow, and dbt, building batch and streaming pipelines on a bronze / silver / gold layout. I'm fairly opinionated about data quality, so I lean on Great Expectations checks, dead letter queues, and schema validation to stop bad rows before they reach a report.

So far I've shipped pipelines handling anywhere from 500K to 44M+ rows across government APIs, e-commerce reviews, and enterprise delivery data.

<img width="100%" src="https://capsule-render.vercel.app/api?type=rect&height=3&color=0:1ba1e3,50:9168cf,100:ec5f78&animation=twinkling"/>

## Tech Stack

**Languages**
<p>
  <img src="https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
  <img src="https://img.shields.io/badge/SQL-005C84?style=for-the-badge&logo=postgresql&logoColor=white"/>
  <img src="https://img.shields.io/badge/PySpark-E25A1C?style=for-the-badge&logo=apachespark&logoColor=white"/>
</p>

**Orchestration & Pipelines**
<p>
  <img src="https://img.shields.io/badge/Apache%20Kafka-231F20?style=for-the-badge&logo=apachekafka&logoColor=white"/>
  <img src="https://img.shields.io/badge/Apache%20Airflow-017CEE?style=for-the-badge&logo=apacheairflow&logoColor=white"/>
  <img src="https://img.shields.io/badge/dbt-FF694B?style=for-the-badge&logo=dbt&logoColor=white"/>
  <img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white"/>
  <img src="https://img.shields.io/badge/Great%20Expectations-FF6310?style=for-the-badge&logo=greatexpectations&logoColor=white"/>
</p>

**Storage & Warehouse**
<p>
  <img src="https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white"/>
  <img src="https://img.shields.io/badge/Snowflake-29B5E8?style=for-the-badge&logo=snowflake&logoColor=white"/>
  <img src="https://img.shields.io/badge/BigQuery-669DF6?style=for-the-badge&logo=googlebigquery&logoColor=white"/>
  <img src="https://img.shields.io/badge/Databricks-FF3621?style=for-the-badge&logo=databricks&logoColor=white"/>
</p>

**Cloud & Visualization**
<p>
  <img src="https://img.shields.io/badge/AWS-232F3E?style=for-the-badge&logo=amazonaws&logoColor=white"/>
  <img src="https://img.shields.io/badge/Google%20Cloud-4285F4?style=for-the-badge&logo=googlecloud&logoColor=white"/>
  <img src="https://img.shields.io/badge/Power%20BI-F2C811?style=for-the-badge&logo=powerbi&logoColor=black"/>
  <img src="https://img.shields.io/badge/Tableau-E97627?style=for-the-badge&logo=tableau&logoColor=white"/>
</p>

<img width="100%" src="https://capsule-render.vercel.app/api?type=rect&height=3&color=0:1ba1e3,50:9168cf,100:ec5f78&animation=twinkling"/>

## Projects

### [Semiconductor Supply Chain Intelligence Platform](https://github.com/narasimha-31)
A streaming pipeline that pulls semiconductor trade and regulatory data from three US government APIs (Census Trade, Federal Register, SEC EDGAR) into PostgreSQL through Kafka. dbt handles the downstream models, Great Expectations catches schema changes before they break anything, and the whole stack runs in Docker.
> `Python` `Kafka` `Airflow` `PostgreSQL` `dbt` `Great Expectations` `Docker`

### [Amazon Review Sentiment Analysis Pipeline](https://github.com/narasimha-31/Amazon_Reviews_ETL_Analytics)
An Airflow pipeline that loads 44.2M Amazon reviews into PostgreSQL with keyset pagination so it doesn't fall over on the volume. Malformed rows get routed to a dead letter queue (about 6,200 of them), and a sentiment model on the gold layer flags reviewer accounts that look fake.
> `Python` `PostgreSQL` `Airflow` `Docker` `VADER` `Power BI`

### [Airline Traffic Analysis](https://github.com/narasimha-31/Airline_Data_Analysis)
Cut 3.3M rows of US DOT airline data down to about 1.1M clean records with Spark, then built a Tableau view covering 34 years of passenger and cargo trends by quarter and carrier.
> `PySpark` `Python` `Tableau`

<img width="100%" src="https://capsule-render.vercel.app/api?type=rect&height=3&color=0:1ba1e3,50:9168cf,100:ec5f78&animation=twinkling"/>

## Experience

**Instructional Assistant, Data Systems & Analytics** · University of Houston · *Apr 2025 to May 2026*
- Designed and migrated the database schema for a nonprofit client (ESCH), turning scattered records into one clean reporting layer.
- Reviewed SQL and database design for around 15 student project teams, and wrote a Python script that checks their query output and run times against a reference schema.

**Graduate Assistant, Systems Data Operations** · University of Houston · *Dec 2024 to Apr 2025*
- Wrote Python to turn daily logs from a 600 user lab into queryable SQL tables.
- Built an incident tracking database from error logs that pinned down about 15 machines quietly dropping connections.

**Data Analyst** · Zensar Technologies · *Mar 2023 to Apr 2024*
- Replaced a manual Excel process with a Python script and took daily report prep from roughly 3 hours to under 20 minutes.
- Wrote SQL validation across 5 source systems that caught around 150 bad records a week before they hit the dashboards, and built Power BI SLA reports that dropped ad hoc requests from about 15 a week to 2 or 3.

<img width="100%" src="https://capsule-render.vercel.app/api?type=rect&height=3&color=0:1ba1e3,50:9168cf,100:ec5f78&animation=twinkling"/>

## Stats & Activity

<p align="center">
  <img height="165" src="https://github-readme-stats.vercel.app/api?username=narasimha-31&show_icons=true&hide_border=true&theme=tokyonight&icon_color=24A99F&title_color=9168cf"/>
  <img height="165" src="https://github-readme-streak-stats.herokuapp.com/?user=narasimha-31&hide_border=true&theme=tokyonight&ring=9168cf&fire=ec5f78&currStreakLabel=24A99F"/>
</p>

<img width="100%" src="https://github-readme-activity-graph.vercel.app/graph?username=narasimha-31&bg_color=0d1117&color=24A99F&line=9168cf&point=ec5f78&area=true&hide_border=true"/>
