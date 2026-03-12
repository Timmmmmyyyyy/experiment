#!/usr/bin/env python3
"""
Generate HTML Dashboard from Benchmark Results
"""
import os
import csv
import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

# Task type Russian labels
TASK_TYPE_LABELS = {
    'Logical': 'Логические',
    'Parsing': 'Извлечение сущности',
    'Transliteration': 'Транслиттерация',
    'Sorting': 'Сортировка',
    'Matching': 'Сопоставление'
}

def parse_csv_results(results_dir):
    """Parse all CSV files in the results directory"""
    # Dictionary to store the best result for each model name
    # model_name -> result_dict
    model_groups = {}
    
    for csv_file in Path(results_dir).glob("*.csv"):
        if csv_file.name == "dashboard.html":
            continue
            
        try:
            # Extract model name from filename: model_name_YYYYMMDD_HHMMSS.csv
            # We look for the pattern _\d{8}_\d{6} at the end
            import re
            filename_stem = csv_file.stem
            match = re.search(r'^(.*)_\d{8}_\d{6}$', filename_stem)
            if match:
                model_name = match.group(1)
            else:
                model_name = filename_stem
                
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
                
                if not rows:
                    continue
                
                # Calculate metrics
                scores = [float(row.get('score', 0)) for row in rows if row.get('score')]
                times = [float(row.get('time_sec', 0)) for row in rows if row.get('time_sec')]
                
                timestamp = rows[0].get('timestamp', '')
                
                task_types = {}
                for row in rows:
                    task_type = row.get('type', 'Unknown')
                    if task_type not in task_types:
                        task_types[task_type] = []
                    if row.get('score'):
                        task_types[task_type].append(float(row['score']))
                
                task_type_scores = {}
                for task_type, type_scores in task_types.items():
                    if type_scores:
                        task_type_scores[task_type] = sum(type_scores) / len(type_scores)
                
                current_result = {
                    'file': csv_file.name,
                    'model': model_name,
                    'total_tasks': len(rows),
                    'avg_score': sum(scores) / len(scores) if scores else 0,
                    'avg_time': sum(times) / len(times) if times else 0,
                    'timestamp': timestamp,
                    'scores': scores,
                    'task_type_scores': task_type_scores,
                }
                
                # Decision logic: keep the result with more tasks, or the newer one if tasks are equal
                if model_name not in model_groups:
                    model_groups[model_name] = current_result
                else:
                    existing = model_groups[model_name]
                    if current_result['total_tasks'] > existing['total_tasks']:
                        model_groups[model_name] = current_result
                    elif current_result['total_tasks'] == existing['total_tasks']:
                        if current_result['timestamp'] > existing['timestamp']:
                            model_groups[model_name] = current_result
        
        except Exception as e:
            print(f"Error processing {csv_file}: {e}")
            continue
    
    # Convert back to list and sort by average score descending
    results = list(model_groups.values())
    results.sort(key=lambda x: x['avg_score'], reverse=True)
    return results

def generate_html_dashboard(results, output_file):
    """Generate HTML dashboard"""
    
    # Get all unique task types across all results
    all_task_types_set = set()
    for result in results:
        all_task_types_set.update(result['task_type_scores'].keys())
    
    # Filter and sort task types based on TASK_TYPE_LABELS
    sorted_task_types = [tt for tt in TASK_TYPE_LABELS.keys() if tt in all_task_types_set]
    # Add any unknown types at the end
    sorted_task_types += sorted(list(all_task_types_set - set(TASK_TYPE_LABELS.keys())))
    
    task_type_labels_js = [TASK_TYPE_LABELS.get(tt, tt) for tt in sorted_task_types]
    
    # Format all results for JavaScript
    json_results = []
    for r in results:
        json_results.append({
            'model': r['model'],
            'avg_score': round(r['avg_score'] * 100, 1),
            'avg_time': round(r['avg_time'], 3),
            'task_scores': [round(r['task_type_scores'].get(tt, 0) * 100, 1) for tt in sorted_task_types]
        })

    html = f"""<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Model Benchmark Dashboard 2.0</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        :root {{
            --glass-bg: rgba(255, 255, 255, 0.05);
            --glass-border: rgba(255, 255, 255, 0.1);
            --glass-shadow: 0 8px 32px 0 rgba(31, 38, 135, 0.37);
            --accent-primary: #00d2ff;
            --accent-secondary: #3a7bd5;
            --text-primary: #ffffff;
            --text-secondary: #cbd5e1;
        }}

        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Inter', -apple-system, sans-serif;
            background: #000;
            color: var(--text-primary);
            min-height: 100vh;
            padding: 40px 20px;
            scroll-behavior: smooth;
            position: relative;
        }}

        .model-selector-container {{
            position: relative;
            width: 300px;
        }}

        /* Subtle Background Elements */
        body::before {{
            content: '';
            position: fixed;
            top: -10%;
            left: -10%;
            width: 40%;
            height: 40%;
            background: radial-gradient(circle, rgba(0, 210, 255, 0.15) 0%, transparent 70%);
            z-index: -1;
            filter: blur(60px);
        }}

        .lang-switcher {{
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 1000;
            display: flex;
            gap: 8px;
            background: rgba(255, 255, 255, 0.05);
            padding: 6px;
            border-radius: 12px;
            border: 1px solid var(--glass-border);
            backdrop-filter: blur(8px);
        }}

        .lang-btn {{
            padding: 6px 14px;
            border-radius: 8px;
            cursor: pointer;
            font-size: 0.8rem;
            font-weight: 700;
            transition: all 0.2s;
            color: var(--text-secondary);
        }}

        .lang-btn.active {{
            background: var(--accent-primary);
            color: #0f172a;
        }}

        .lang-btn:not(.active):hover {{
            background: rgba(255, 255, 255, 0.1);
            color: #fff;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        .glass {{
            background: var(--glass-bg);
            backdrop-filter: blur(12px);
            -webkit-backdrop-filter: blur(12px);
            border: 1px solid var(--glass-border);
            border-radius: 24px;
            padding: 32px;
            box-shadow: var(--glass-shadow);
            margin-bottom: 40px;
        }}
        
        header {{
            text-align: center;
            margin-bottom: 80px;
            padding: 80px 20px;
            position: relative;
            overflow: hidden;
            border-radius: 40px;
            background: rgba(255, 255, 255, 0.02);
            border: 1px solid var(--glass-border);
            backdrop-filter: blur(10px);
        }}

        .header-bg {{
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            z-index: 0;
            pointer-events: none;
        }}
        
        header h1 {{
            font-size: 5rem;
            font-weight: 900;
            background: linear-gradient(135deg, #fff 0%, #00d2ff 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 20px;
            letter-spacing: -3px;
            filter: drop-shadow(0 10px 20px rgba(0,0,0,0.5));
            position: relative;
            z-index: 1;
        }}
        
        header p {{
            color: #fff;
            font-size: 1.4rem;
            max-width: 700px;
            margin: 0 auto;
            opacity: 0.8;
            font-weight: 500;
            position: relative;
            z-index: 1;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 24px;
            margin-bottom: 60px;
        }}
        
        .stat-card:hover {{
            transform: translateY(-5px);
            background: rgba(255, 255, 255, 0.08);
            transition: all 0.3s ease;
        }}
        
        .stat-value {{
            font-size: 3.5rem;
            font-weight: 800;
            display: block;
            margin-bottom: 4px;
            color: #fff;
            text-shadow: 0 0 20px rgba(0, 210, 255, 0.3);
        }}
        
        .stat-label {{
            color: var(--accent-primary);
            text-transform: uppercase;
            font-size: 0.75rem;
            font-weight: 800;
            letter-spacing: 2px;
        }}
        
        .grid-2 {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 32px;
            margin-bottom: 40px;
        }}
        
        .chart-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 24px;
        }}
        
        .chart-title {{
            font-size: 1.5rem;
            font-weight: 700;
            color: #fff;
        }}

        .time-chart-container {{
            position: relative;
            min-height: 400px;
            width: 100%;
        }}
        
        .btn {{
            background: rgba(255, 255, 255, 0.1);
            border: 1px solid var(--glass-border);
            color: #fff;
            padding: 10px 18px;
            border-radius: 12px;
            font-size: 0.85rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
        }}
        
        .btn:hover {{
            background: rgba(255, 255, 255, 0.2);
            border-color: var(--accent-primary);
        }}
        
        .multi-select-dropdown {{
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 16px;
            margin-top: 8px;
            max-height: 350px;
            overflow-y: auto;
            z-index: 1000;
            display: none;
            padding: 10px;
            box-shadow: 0 10px 25px rgba(0,0,0,0.5);
            backdrop-filter: blur(20px);
        }}
        
        .model-option {{
            display: flex;
            align-items: center;
            padding: 10px 12px;
            border-radius: 10px;
            cursor: pointer;
            transition: background 0.2s;
        }}
        
        .model-option:hover {{
            background: rgba(255, 255, 255, 0.1);
        }}
        
        .model-option input {{
            width: 16px;
            height: 16px;
            margin-right: 12px;
            accent-color: var(--accent-primary);
        }}
        
        table {{
            width: 100%;
            border-collapse: separate;
            border-spacing: 0 10px;
        }}
        
        th {{
            padding: 16px;
            text-align: left;
            color: var(--text-secondary);
            font-weight: 700;
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 1px;
        }}
        
        tr.table-row {{
            background: rgba(255, 255, 255, 0.03);
            transition: all 0.2s ease;
        }}
        
        tr.table-row:hover {{
            background: rgba(255, 255, 255, 0.07);
            transform: scale(1.005);
        }}
        
        td {{
            padding: 20px 16px;
        }}
        
        td:first-child {{ border-radius: 16px 0 0 16px; font-weight: 800; color: var(--accent-primary); }}
        td:last-child {{ border-radius: 0 16px 16px 0; }}
        
        .score-pill {{
            background: rgba(0, 210, 255, 0.1);
            color: var(--accent-primary);
            padding: 6px 14px;
            border-radius: 12px;
            font-weight: 700;
            display: inline-block;
            border: 1px solid rgba(0, 210, 255, 0.2);
        }}
        
        .time-text {{
            font-family: 'JetBrains Mono', monospace;
            color: var(--text-secondary);
        }}
        
        .animate-in {{
            animation: fadeIn 0.8s ease-out forwards;
            opacity: 0;
        }}
        
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        /* Scroll Reveal Styles */
        .reveal {{
            opacity: 0;
            transform: translateY(30px);
            transition: all 1s cubic-bezier(0.2, 0.8, 0.2, 1);
        }}

        .reveal.active {{
            opacity: 1;
            transform: translateY(0);
        }}
        
        @media (max-width: 1100px) {{
            .grid-2 {{ grid-template-columns: 1fr; }}
            header h1 {{ font-size: 2.8rem; }}
        }}
    </style>
</head>
<body>
    <div class="lang-switcher">
        <div class="lang-btn active" onclick="setLanguage('ru')">RU</div>
        <div class="lang-btn" onclick="setLanguage('uz')">UZ</div>
    </div>

    <div class="container">
        <header class="animate-in" id="dashboardHeader">
            <canvas id="headerCanvas" class="header-bg"></canvas>
            <h1 data-i18n="header_title">LLM Benchmark</h1>
            <p data-i18n="header_subtitle">Комплексный анализ производительности и точности моделей на базе 100 задач</p>
        </header>

        <div class="stats-grid">
            <div class="glass stat-card reveal">
                <span class="stat-value" id="topScore">{results[0]['avg_score']:.1%}</span>
                <span class="stat-label" data-i18n="stat_max_accuracy">Макс. точность</span>
            </div>
            <div class="glass stat-card reveal">
                <span class="stat-value">{len(results)}</span>
                <span class="stat-label" data-i18n="stat_models_count">Моделей в базе</span>
            </div>
            <div class="glass stat-card reveal">
                <span class="stat-value" id="avgTime">{sum(r['avg_time'] for r in results)/len(results):.2f}s</span>
                <span class="stat-label" data-i18n="stat_avg_time">Среднее время ответа</span>
            </div>
            <div class="glass stat-card reveal">
                <span class="stat-value">{sum(r['total_tasks'] for r in results)}</span>
                <span class="stat-label" data-i18n="stat_tasks_solved">Решенных задач</span>
            </div>
        </div>

        <div class="grid-2">
            <div class="glass reveal" style="transition-delay: 0.1s">
                <div class="chart-header">
                    <h2 class="chart-title" data-i18n="chart_radar_title">🎯 Сравнение способностей</h2>
                    <div class="model-selector-container">
                        <div id="selectorBtn" class="btn" data-i18n="btn_radar_select">Выбор моделей для радара ▾</div>
                        <div id="dropdown" class="multi-select-dropdown">
                            <!-- Options injected by JS -->
                        </div>
                    </div>
                </div>
                <canvas id="radarChart"></canvas>
            </div>

            <div class="glass reveal" style="transition-delay: 0.2s">
                <div class="chart-header">
                    <h2 class="chart-title" data-i18n="chart_time_title">⚡ Время выполнения</h2>
                    <div class="model-selector-container">
                        <div id="timeSelectorBtn" class="btn" data-i18n="btn_time_select">Выбор моделей для времени ▾</div>
                        <div id="timeDropdown" class="multi-select-dropdown">
                            <!-- Options injected by JS -->
                        </div>
                    </div>
                </div>
                <div class="time-chart-container">
                    <canvas id="timeChart"></canvas>
                </div>
            </div>
        </div>

        <div class="glass reveal" style="transition-delay: 0.3s">
            <h2 class="chart-title" style="margin-bottom: 24px" data-i18n="table_title">🏆 Глобальный рейтинг</h2>
            <table>
                <thead>
                    <tr>
                        <th style="width: 60px">#</th>
                        <th data-i18n="th_model">Модель</th>
                        <th data-i18n="th_score">Ср. балл</th>
                        <th data-i18n="th_time">Время ответа</th>
                        <th data-i18n="th_efficiency">Эффективность (Балы/сек)</th>
                    </tr>
                </thead>
                <tbody id="rankingTable">
                    <!-- Rows injected by JS -->
                </tbody>
            </table>
        </div>
    </div>

    <script>
        const allData = {json.dumps(json_results)};
        const taskLabels = {json.dumps(task_type_labels_js)};
        
        const translations = {{
            ru: {{
                header_title: "LLM Benchmark",
                header_subtitle: "Комплексный анализ производительности и точности моделей на базе 100 задач",
                stat_max_accuracy: "Макс. точность",
                stat_models_count: "Моделей в базе",
                stat_avg_time: "Среднее время ответа",
                stat_tasks_solved: "Решенных задач",
                chart_radar_title: "🎯 Сравнение способностей",
                chart_time_title: "⚡ Время выполнения",
                btn_radar_select: "Выбор моделей для радара ▾",
                btn_time_select: "Выбор моделей для времени ▾",
                table_title: "🏆 Глобальный рейтинг",
                th_model: "Модель",
                th_score: "Ср. балл",
                th_time: "Время ответа",
                th_efficiency: "Эффективность (Балы/сек)",
                select_all: "Выбрать всё",
                avg_time_label: "Среднее время (сек)"
            }},
            uz: {{
                header_title: "LLM Benchmark",
                header_subtitle: "100 ta topshiriq asosida modellarning ishlashi va aniqligini har tomonlama tahlil qilish",
                stat_max_accuracy: "Maks. aniqlik",
                stat_models_count: "Bazadagi modellar",
                stat_avg_time: "O'rtacha javob vaqti",
                stat_tasks_solved: "Yechilgan topshiriqlar",
                chart_radar_title: "🎯 Qobiliyatlarni solishtirish",
                chart_time_title: "⚡ Bajarilish vaqti",
                btn_radar_select: "Radar uchun modellarni tanlash ▾",
                btn_time_select: "Vaqt uchun modellarni tanlash ▾",
                table_title: "🏆 Global reyting",
                th_model: "Model",
                th_score: "O'rtacha ball",
                th_time: "Javob vaqti",
                th_efficiency: "Samaradorlik (Ball/sek)",
                select_all: "Hammasini tanlash",
                avg_time_label: "O'rtacha vaqt (sek)"
            }}
        }};

        let currentLang = 'ru';
        let selectedModels = allData.slice(0, 5).map(m => m.model);
        let selectedTimeModels = allData.map(m => m.model);
        let radarChart, timeChart;

        function setLanguage(lang) {{
            currentLang = lang;
            
            // Update active state of buttons
            document.querySelectorAll('.lang-btn').forEach(btn => {{
                btn.classList.toggle('active', btn.textContent.toLowerCase() === lang);
            }});

            // Update text elements
            document.querySelectorAll('[data-i18n]').forEach(el => {{
                const key = el.getAttribute('data-i18n');
                if (translations[lang][key]) {{
                    el.textContent = translations[lang][key];
                }}
            }});

            // Update selectors
            populateDropdowns();
            
            // Update charts
            if (timeChart) {{
                timeChart.data.datasets[0].label = translations[lang].avg_time_label;
                timeChart.update();
            }}
        }}

        // Initialize UI
        function initApp() {{
            populateDropdowns();
            renderRadar();
            renderTimeChart();
            renderTable();
            
            // Radar selector
            document.getElementById('selectorBtn').onclick = () => {{
                const dd = document.getElementById('dropdown');
                dd.style.display = dd.style.display === 'block' ? 'none' : 'block';
                document.getElementById('timeDropdown').style.display = 'none';
            }};
            
            // Time selector
            document.getElementById('timeSelectorBtn').onclick = () => {{
                const dd = document.getElementById('timeDropdown');
                dd.style.display = dd.style.display === 'block' ? 'none' : 'block';
                document.getElementById('dropdown').style.display = 'none';
            }};
            
            window.onclick = (e) => {{
                if (!e.target.matches('#selectorBtn') && !e.target.closest('#dropdown') &&
                    !e.target.matches('#timeSelectorBtn') && !e.target.closest('#timeDropdown')) {{
                    document.getElementById('dropdown').style.display = 'none';
                    document.getElementById('timeDropdown').style.display = 'none';
                }}
            }};

            // Scroll Reveal Logic
            const revealCallback = (entries, observer) => {{
                entries.forEach(entry => {{
                    if (entry.isIntersecting) {{
                        entry.target.classList.add('active');
                        observer.unobserve(entry.target);
                    }}
                }});
            }};

            const revealObserver = new IntersectionObserver(revealCallback, {{
                threshold: 0.15
            }});

            document.querySelectorAll('.reveal').forEach(el => {{
                revealObserver.observe(el);
            }});

            initHeaderAnimation();
        }}

        function initHeaderAnimation() {{
            const canvas = document.getElementById('headerCanvas');
            const ctx = canvas.getContext('2d');
            const header = document.getElementById('dashboardHeader');
            
            let particles = [];
            const mouse = {{ x: -1000, y: -1000, radius: 120, active: false }};
            const colors = ['#4285F4', '#EA4335', '#FBBC05', '#34A853', '#673AB7'];
            
            const SPRING_STRENGTH = 0.04;
            const DAMPING = 0.94;
            const MOUSE_INFLUENCE = 250;
            const PARTICLE_DENSITY = 20;

            window.addEventListener('mousemove', (e) => {{
                const rect = canvas.getBoundingClientRect();
                mouse.x = e.clientX - rect.left;
                mouse.y = e.clientY - rect.top;
                mouse.active = true;
            }});

            function resize() {{
                const rect = header.getBoundingClientRect();
                canvas.width = rect.width;
                canvas.height = rect.height;
                initGrid();
            }}

            window.addEventListener('resize', resize);

            class Particle {{
                constructor(x, y, row, col) {{
                    this.originalX = x;
                    this.originalY = y;
                    this.x = x;
                    this.y = y;
                    this.vx = 0;
                    this.vy = 0;
                    this.row = row;
                    this.col = col;
                    this.color = colors[Math.floor(Math.random() * colors.length)];
                    this.baseSize = Math.random() * 1.5 + 1;
                    
                    // Organic breathing parameters
                    this.phaseX = Math.random() * Math.PI * 2;
                    this.phaseY = Math.random() * Math.PI * 2;
                    this.freqX = Math.random() * 0.015 + 0.008;
                    this.freqY = Math.random() * 0.015 + 0.008;
                    this.amplitude = Math.random() * 2 + 1;
                }}

                update(time) {{
                    // Organic breathing motion
                    const breathX = Math.sin(time * this.freqX + this.phaseX) * this.amplitude;
                    const breathY = Math.cos(time * this.freqY + this.phaseY) * this.amplitude;
                    
                    // Wave propagation across grid
                    const waveX = Math.sin(time * 0.5 + this.col * 0.3) * 1.5;
                    const waveY = Math.cos(time * 0.5 + this.row * 0.3) * 1.5;
                    
                    const targetX = this.originalX + breathX + waveX;
                    const targetY = this.originalY + breathY + waveY;
                    
                    const dxToOriginal = targetX - this.x;
                    const dyToOriginal = targetY - this.y;
                    this.vx += dxToOriginal * SPRING_STRENGTH;
                    this.vy += dyToOriginal * SPRING_STRENGTH;

                    if (mouse.active) {{
                        const dxToMouse = this.x - mouse.x;
                        const dyToMouse = this.y - mouse.y;
                        const distanceToMouse = Math.sqrt(dxToMouse * dxToMouse + dyToMouse * dyToMouse);

                        if (distanceToMouse < mouse.radius) {{
                            const force = MOUSE_INFLUENCE / (distanceToMouse * distanceToMouse + 1);
                            this.vx += (dxToMouse * force);
                            this.vy += (dyToMouse * force);
                        }}
                    }}
                    
                    this.vx *= DAMPING;
                    this.vy *= DAMPING;
                    this.x += this.vx;
                    this.y += this.vy;
                }}

                draw() {{
                    const speed = Math.sqrt(this.vx * this.vx + this.vy * this.vy);
                    const length = Math.min(speed * 8, 30);
                    
                    if (length < 0.5) {{
                        // Draw as point if barely moving
                        ctx.beginPath();
                        ctx.arc(this.x, this.y, this.baseSize * 0.5, 0, Math.PI * 2);
                        ctx.fillStyle = this.color;
                        ctx.fill();
                        return;
                    }}
                    
                    const angle = Math.atan2(this.vy, this.vx);
                    
                    ctx.save();
                    ctx.translate(this.x, this.y);
                    ctx.rotate(angle);

                    const gradient = ctx.createLinearGradient(0, 0, length, 0);
                    gradient.addColorStop(0, this.color);
                    gradient.addColorStop(0.6, this.color);
                    gradient.addColorStop(1, 'rgba(0,0,0,0)');

                    ctx.beginPath();
                    ctx.strokeStyle = gradient;
                    ctx.lineWidth = this.baseSize;
                    ctx.lineCap = 'round';
                    ctx.moveTo(0, 0);
                    ctx.lineTo(length, 0);
                    ctx.globalAlpha = 0.75;
                    ctx.stroke();
                    ctx.globalAlpha = 1;
                    
                    ctx.restore();
                }}
            }}

            function initGrid() {{
                particles = [];

                const numRows = Math.floor(canvas.height / PARTICLE_DENSITY);
                const numCols = Math.floor(canvas.width / PARTICLE_DENSITY);

                for (let r = 0; r <= numRows; r++) {{
                    for (let c = 0; c <= numCols; c++) {{
                        const x = c * PARTICLE_DENSITY;
                        const y = r * PARTICLE_DENSITY;
                        particles.push(new Particle(x, y, r, c));
                    }}
                }}
            }}

            let startTime = Date.now();
            function animate() {{
                const time = (Date.now() - startTime) * 0.001;
                ctx.clearRect(0, 0, canvas.width, canvas.height);

                particles.forEach(p => {{
                    p.update(time);
                    p.draw();
                }});

                requestAnimationFrame(animate);
            }}

            resize();
            animate();
        }}


        function populateDropdowns() {{
            const radarDd = document.getElementById('dropdown');
            const timeDd = document.getElementById('timeDropdown');
            
            radarDd.innerHTML = '';
            timeDd.innerHTML = '';

            // --- Radar Select All ---
            const radarAllDiv = document.createElement('div');
            radarAllDiv.className = 'model-option';
            radarAllDiv.style.borderBottom = '1px solid rgba(255,255,255,0.1)';
            radarAllDiv.style.marginBottom = '4px';
            radarAllDiv.innerHTML = `<input type="checkbox" id="radarSelectAll"> <strong data-i18n="select_all">${{translations[currentLang].select_all}}</strong>`;
            radarAllDiv.onclick = (e) => {{
                const cb = radarAllDiv.querySelector('input');
                if (e.target !== cb) cb.checked = !cb.checked;
                const allCbs = radarDd.querySelectorAll('input:not(#radarSelectAll)');
                allCbs.forEach(c => c.checked = cb.checked);
                updateSelection();
            }};
            radarDd.appendChild(radarAllDiv);

            // --- Time Select All ---
            const timeAllDiv = document.createElement('div');
            timeAllDiv.className = 'model-option';
            timeAllDiv.style.borderBottom = '1px solid rgba(255,255,255,0.1)';
            timeAllDiv.style.marginBottom = '4px';
            timeAllDiv.innerHTML = `<input type="checkbox" id="timeSelectAll"> <strong data-i18n="select_all">${{translations[currentLang].select_all}}</strong>`;
            timeAllDiv.onclick = (e) => {{
                const cb = timeAllDiv.querySelector('input');
                if (e.target !== cb) cb.checked = !cb.checked;
                const allCbs = timeDd.querySelectorAll('input:not(#timeSelectAll)');
                allCbs.forEach(c => c.checked = cb.checked);
                updateTimeSelection();
            }};
            timeDd.appendChild(timeAllDiv);
            
            allData.forEach(model => {{
                // Radar Option
                const radarDiv = document.createElement('div');
                radarDiv.className = 'model-option';
                const radarChecked = selectedModels.includes(model.model) ? 'checked' : '';
                radarDiv.innerHTML = `<input type="checkbox" value="${{model.model}}" ${{radarChecked}}> ${{model.model}}`;
                radarDiv.onclick = (e) => {{
                    const cb = radarDiv.querySelector('input');
                    if (e.target !== cb) cb.checked = !cb.checked;
                    updateSelection();
                }};
                radarDd.appendChild(radarDiv);
                
                // Time Option
                const timeDiv = document.createElement('div');
                timeDiv.className = 'model-option';
                const timeChecked = selectedTimeModels.includes(model.model) ? 'checked' : '';
                timeDiv.innerHTML = `<input type="checkbox" value="${{model.model}}" ${{timeChecked}}> ${{model.model}}`;
                timeDiv.onclick = (e) => {{
                    const cb = timeDiv.querySelector('input');
                    if (e.target !== cb) cb.checked = !cb.checked;
                    updateTimeSelection();
                }};
                timeDd.appendChild(timeDiv);
            }});

            // Initial state for "Select All"
            updateSelectAllState('radarSelectAll', '#dropdown');
            updateSelectAllState('timeSelectAll', '#timeDropdown');
        }}

        function updateSelectAllState(selectAllId, containerId) {{
            const selectAllCb = document.getElementById(selectAllId);
            const allCbs = document.querySelectorAll(`${{containerId}} input:not(#${{selectAllId}})`);
            const checkedCbs = document.querySelectorAll(`${{containerId}} input:checked:not(#${{selectAllId}})`);
            selectAllCb.checked = allCbs.length \u003e 0 && allCbs.length === checkedCbs.length;
            selectAllCb.indeterminate = checkedCbs.length \u003e 0 && checkedCbs.length \u003c allCbs.length;
        }}

        function updateSelection() {{
            const checkboxes = document.querySelectorAll('#dropdown input:checked:not(#radarSelectAll)');
            selectedModels = Array.from(checkboxes).map(cb => cb.value);
            updateRadar();
            updateSelectAllState('radarSelectAll', '#dropdown');
        }}
        
        function updateTimeSelection() {{
            const checkboxes = document.querySelectorAll('#timeDropdown input:checked:not(#timeSelectAll)');
            selectedTimeModels = Array.from(checkboxes).map(cb => cb.value);
            updateTimeChart();
            updateSelectAllState('timeSelectAll', '#timeDropdown');
        }}

        function renderRadar() {{
            const datasets = allData.filter(m => selectedModels.includes(m.model)).map((m, i) => ({{
                label: m.model,
                data: m.task_scores,
                fill: true,
                backgroundColor: getPalette(i, 0.3),
                borderColor: getPalette(i, 1),
                pointBackgroundColor: getPalette(i, 1),
                borderWidth: 2
            }}));

            const ctx = document.getElementById('radarChart').getContext('2d');
            radarChart = new Chart(ctx, {{
                type: 'radar',
                data: {{ labels: taskLabels, datasets }},
                options: {{
                    scales: {{
                        r: {{
                            angleLines: {{ color: 'rgba(255,255,255,0.1)' }},
                            grid: {{ color: 'rgba(255,255,255,0.1)' }},
                            pointLabels: {{ color: '#94a3b8', font: {{ size: 12 }} }},
                            ticks: {{ display: false }},
                            suggestedMin: 0,
                            suggestedMax: 100
                        }}
                    }},
                    plugins: {{
                        legend: {{
                            display: true,
                            labels: {{ color: '#f1f5f9', usePointStyle: true }}
                        }}
                    }}
                }}
            }});
        }}

        function updateRadar() {{
            const datasets = allData.filter(m => selectedModels.includes(m.model)).map((m, i) => ({{
                label: m.model,
                data: m.task_scores,
                fill: true,
                backgroundColor: getPalette(i, 0.3),
                borderColor: getPalette(i, 1),
                pointBackgroundColor: getPalette(i, 1),
                borderWidth: 2
            }}));
            radarChart.data.datasets = datasets;
            radarChart.update();
        }}

        function renderTimeChart() {{
            const chartData = allData.filter(m => selectedTimeModels.includes(m.model)).sort((a, b) => a.avg_time - b.avg_time);
            const ctx = document.getElementById('timeChart').getContext('2d');
            
            // Adjust height based on model count
            const container = ctx.canvas.parentElement;
            container.style.height = `${{Math.max(400, chartData.length * 35)}}px`;

            timeChart = new Chart(ctx, {{
                type: 'bar',
                data: {{
                    labels: chartData.map(m => m.model),
                    datasets: [{{
                        label: translations[currentLang].avg_time_label,
                        data: chartData.map(m => m.avg_time),
                        backgroundColor: chartData.map((_, i) => i === 0 ? '#38bdf8' : 'rgba(56, 189, 248, 0.4)'),
                        borderRadius: 12
                    }}]
                }},
                options: {{
                    indexAxis: 'y',
                    maintainAspectRatio: false,
                    responsive: true,
                    plugins: {{ legend: {{ display: false }} }},
                    scales: {{
                        x: {{ 
                            grid: {{ color: 'rgba(255,255,255,0.05)' }},
                            ticks: {{ color: '#64748b' }}
                        }},
                        y: {{ 
                            grid: {{ display: false }},
                            ticks: {{ 
                                color: '#f1f5f9',
                                autoSkip: false,
                                font: {{ size: 11 }}
                            }}
                        }}
                    }}
                }}
            }});
        }}

        function updateTimeChart() {{
            const chartData = allData.filter(m => selectedTimeModels.includes(m.model)).sort((a, b) => a.avg_time - b.avg_time);
            const container = timeChart.canvas.parentElement;
            container.style.height = `${{Math.max(400, chartData.length * 35)}}px`;
            
            timeChart.data.labels = chartData.map(m => m.model);
            timeChart.data.datasets[0].data = chartData.map(m => m.avg_time);
            timeChart.data.datasets[0].backgroundColor = chartData.map((_, i) => i === 0 ? '#38bdf8' : 'rgba(56, 189, 248, 0.4)');
            timeChart.update();
        }}

        function renderTable() {{
            const tbody = document.getElementById('rankingTable');
            allData.forEach((m, i) => {{
                const efficiency = (m.avg_score / (m.avg_time || 1)).toFixed(2);
                const tr = document.createElement('tr');
                tr.className = 'table-row';
                tr.innerHTML = `
                    <td>${{i+1}}</td>
                    <td><strong>${{m.model}}</strong></td>
                    <td><span class="score-pill">${{m.avg_score}}%</span></td>
                    <td><span class="time-text">${{m.avg_time}}s</span></td>
                    <td>${{efficiency}}</td>
                `;
                tbody.appendChild(tr);
            }});
        }}

        function getPalette(i, alpha) {{
            const colors = [
                `rgba(56, 189, 248, ${{alpha}})`,
                `rgba(129, 140, 248, ${{alpha}})`,
                `rgba(168, 85, 247, ${{alpha}})`,
                `rgba(236, 72, 153, ${{alpha}})`,
                `rgba(248, 113, 113, ${{alpha}})`,
                `rgba(251, 146, 60, ${{alpha}})`,
                `rgba(250, 204, 21, ${{alpha}})`,
                `rgba(74, 222, 128, ${{alpha}})`,
                `rgba(45, 212, 191, ${{alpha}})`
            ];
            return colors[i % colors.length];
        }}

        initApp();
    </script>
</body>
</html>
"""
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"Dashboard generated: {output_file}")

if __name__ == "__main__":
    results_dir = "results"
    output_file = "results/dashboard.html"
    
    results = parse_csv_results(results_dir)
    generate_html_dashboard(results, output_file)
    
    print(f"\n✅ Dashboard 2.0 created successfully!")
    print(f"📊 Processed {len(results)} models")
    print(f"📁 Output: {output_file}")
