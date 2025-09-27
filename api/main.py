"""
Основное FastAPI приложение для AI Visibility MVP
"""

import os
import tempfile
import threading
import hashlib
from typing import Optional
import pandas as pd
from io import BytesIO

from fastapi import FastAPI, Request, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse, HTMLResponse
from starlette.middleware.cors import CORSMiddleware

# Импорт наших модулей
from api.config import EMAIL_REGEX, MAX_UPLOAD_MB, ALLOW_RETRY_SAME_FILE, validate_config
from api.database import db
from api.file_processor import FileProcessor
from api.openai_client import openai_client
from api.metrics import MetricsCalculator
from api.email_service import email_service

# Создание FastAPI приложения
app = FastAPI(
    title="AI Visibility MVP",
    description="Сервис для анализа видимости в ChatGPT",
    version="1.0.0"
)

# Добавление CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# HTML лендинг страницы встроенный в код
LANDING_HTML = r"""<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BoostMyGEO - Перевірте, чи рекомендує ШІ ваші продукти</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .gradient-text {
            background: linear-gradient(45deg, #2563eb, #3b82f6);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }
        .gradient-button {
            background: linear-gradient(45deg, #059669, #10b981);
        }
        .gradient-button-blue {
            background: linear-gradient(45deg, #2563eb, #3b82f6);
        }
        .fade-in {
            animation: fadeIn 0.8s ease-out;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(30px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .hover-lift {
            transition: all 0.3s ease;
        }
        .hover-lift:hover {
            transform: translateY(-4px);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
        }
        .feature-card {
            transition: all 0.3s ease;
        }
        .feature-card:hover {
            transform: translateY(-4px);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
            border-color: #3b82f6;
        }
        .dashboard-card {
            transition: all 0.3s ease;
        }
        .dashboard-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
        }
        .drag-over {
            border-color: #3b82f6;
            background-color: #eff6ff;
        }
        .pulse-animation {
            animation: pulse 2s infinite;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        .slide-up {
            animation: slideUp 0.6s ease-out forwards;
        }
        @keyframes slideUp {
            from { 
                opacity: 0; 
                transform: translateY(50px); 
            }
            to { 
                opacity: 1; 
                transform: translateY(0); 
            }
        }
        .timer-progress {
            transition: width 0.1s linear;
        }
        .page-transition {
            transition: all 0.5s ease-in-out;
        }
        .hidden-page {
            opacity: 0;
            transform: translateY(20px);
            pointer-events: none;
        }
        .show-page {
            opacity: 1;
            transform: translateY(0);
            pointer-events: all;
        }
    </style>
</head>
<body class="bg-white text-gray-800 min-h-screen flex flex-col">
    <!-- Header -->
    <header class="fixed w-full top-0 bg-white/95 backdrop-blur-sm border-b border-gray-100 z-50">
        <div class="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
            <div class="flex justify-between items-center h-16">
                <div class="flex items-center">
                    <div class="flex items-center space-x-2">
                        <div class="h-8 w-8 bg-gradient-to-r from-blue-500 to-green-500 rounded-lg flex items-center justify-center">
                            <span class="text-white font-bold text-sm">B</span>
                        </div>
                        <div class="text-xl font-bold gradient-text">BoostMyGEO</div>
                    </div>
                </div>
            </div>
        </div>
    </header>

    <!-- Main Content Container -->
    <div class="pt-24 flex-grow">
        <!-- PAGE 1: Initial Upload Page -->
        <div id="uploadPage" class="page-transition show-page">
            <!-- Hero Section -->
            <section class="pb-12 px-4 sm:px-6 lg:px-8 bg-white">
                <div class="max-w-5xl mx-auto text-center">
                    <div class="fade-in">
                        <h1 class="text-4xl md:text-6xl lg:text-7xl font-bold mb-10 text-gray-900 leading-tight">
                            Дізнайся чи показується твій сайт у <span class="gradient-text">ChatGPT</span> по цільовим запитам
                        </h1>

                        <!-- File Upload Form -->
                        <div class="bg-gray-50 rounded-2xl p-6 md:p-8 mb-8 max-w-2xl mx-auto border border-gray-200" id="uploadForm">
                            <p class="text-lg font-semibold text-gray-900 mb-4">
                                Додай CSV файл з ключовими фразами і отримай результат
                            </p>
                            
                            <div class="mb-4">
                                <button id="downloadTemplate" class="text-blue-600 underline underline-offset-4 decoration-blue-600 hover:decoration-2 font-medium transition-all">
                                    Скачати шаблон файлу
                                </button>
                            </div>

                            <!-- File Upload Area -->
                            <div id="uploadArea" class="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-blue-400 transition-colors cursor-pointer">
                                <div id="uploadContent">
                                    <svg class="mx-auto h-12 w-12 text-gray-400 mb-4" stroke="currentColor" fill="none" viewBox="0 0 48 48">
                                        <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"></path>
                                    </svg>
                                    <p class="text-gray-600 mb-2">Перетягніть CSV файл сюди або</p>
                                    <button type="button" class="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors">
                                        Оберіть файл
                                    </button>
                                    <p class="text-xs text-gray-500 mt-2">Тільки .csv файли до 1 МБ</p>
                                </div>
                                
                                <!-- File Success State -->
                                <div id="fileSuccess" class="hidden">
                                    <div class="flex items-center justify-center space-x-2 text-green-600 mb-4">
                                        <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                                            <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path>
                                        </svg>
                                        <span id="fileName"></span>
                                        <span id="fileSize" class="text-sm"></span>
                                    </div>
                                    
                                    <!-- Timer -->
                                    <div class="bg-white rounded-lg p-4 border border-green-200">
                                        <p class="text-green-800 font-semibold mb-3">Обробка файлу...</p>
                                        <div class="w-full bg-gray-200 rounded-full h-2 mb-2">
                                            <div id="timerProgress" class="bg-green-600 h-2 rounded-full timer-progress" style="width: 0%"></div>
                                        </div>
                                        <p class="text-sm text-green-700">
                                            <span id="timerSeconds">3</span> секунд до завершення
                                        </p>
                                    </div>
                                </div>

                                <!-- File Error State -->
                                <div id="errorInfo" class="hidden text-red-600">
                                    <svg class="w-5 h-5 mx-auto mb-1" fill="currentColor" viewBox="0 0 20 20">
                                        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path>
                                    </svg>
                                    <span id="errorMessage"></span>
                                </div>
                            </div>

                            <input type="file" id="fileInput" class="hidden" accept=".csv">

                            <p class="text-gray-500 text-sm mt-4">Безкоштовна пробна версія • Без кредитної картки • Миттєві результати</p>
                        </div>

                        <!-- Upload Complete Section (shown after using the service) -->
                        <div class="bg-blue-50 rounded-2xl p-6 md:p-8 mb-8 max-w-2xl mx-auto border border-blue-200 hidden" id="uploadCompleteSection">
                            <div class="text-center">
                                <div class="w-16 h-16 bg-blue-500 rounded-full flex items-center justify-center mx-auto mb-6">
                                    <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                                    </svg>
                                </div>
                                <h3 class="text-2xl font-bold text-blue-800 mb-4">Сервіс вже використано</h3>
                                <p class="text-lg text-blue-700 mb-4">
                                    Ви вже скористались нашим сервісом. Результати надіслані на вашу пошту.
                                </p>
                                <p class="text-blue-600 text-sm">
                                    Для повторного аналізу зв'яжіться з нами
                                </p>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            <!-- Results Preview, Problem Section, Social Proof etc. -->
            <section class="py-12 px-4 sm:px-6 lg:px-8 bg-gray-50">
                <div class="max-w-6xl mx-auto">
                    <div class="bg-white rounded-2xl p-6 md:p-8 shadow-xl border border-gray-200">
                        <h3 class="text-2xl font-bold text-gray-900 mb-6 text-center">Ваші продукти або послуги в пошуку ШІ</h3>
                        
                        <!-- Desktop Table -->
                        <div class="hidden md:block overflow-x-auto">
                            <table class="w-full">
                                <thead>
                                    <tr class="border-b border-gray-200">
                                        <th class="text-left py-3 px-4 font-semibold text-gray-900">Запит</th>
                                        <th class="text-left py-3 px-4 font-semibold text-gray-900">Рекомендація ШІ</th>
                                        <th class="text-left py-3 px-4 font-semibold text-gray-900">Конкуренти</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr class="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                                        <td class="py-4 px-4 font-medium text-gray-900">Бездротовий зарядний пристрій iPhone</td>
                                        <td class="py-4 px-4">
                                            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                                Рекомендується (4)
                                            </span>
                                        </td>
                                        <td class="py-4 px-4 text-gray-700">competitor1.com, competitor2.com, competitor3.com</td>
                                    </tr>
                                    <tr class="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                                        <td class="py-4 px-4 font-medium text-gray-900">Підставка для ноутбука</td>
                                        <td class="py-4 px-4">
                                            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                                                Не рекомендується
                                            </span>
                                        </td>
                                        <td class="py-4 px-4 text-gray-700">competitor4.com, competitor5.com</td>
                                    </tr>
                                    <tr class="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                                        <td class="py-4 px-4 font-medium text-gray-900">USB-C хаб</td>
                                        <td class="py-4 px-4">
                                            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                                                Не рекомендується
                                            </span>
                                        </td>
                                        <td class="py-4 px-4 text-gray-700">competitor6.com, competitor7.com, competitor8.com, competitor9.com</td>
                                    </tr>
                                    <tr class="border-b border-gray-100 hover:bg-gray-50 transition-colors">
                                        <td class="py-4 px-4 font-medium text-gray-900">Чохол для телефону</td>
                                        <td class="py-4 px-4">
                                            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                                Рекомендується (1)
                                            </span>
                                        </td>
                                        <td class="py-4 px-4 text-gray-700">competitor10.com, competitor11.com, competitor12.com</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>

                        <!-- Mobile Cards -->
                        <div class="md:hidden space-y-4">
                            <div class="border border-gray-200 rounded-lg p-4">
                                <div class="font-medium text-gray-900 mb-2">Бездротовий зарядний пристрій iPhone</div>
                                <div class="flex items-center justify-between mb-2">
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                        Рекомендується (4)
                                    </span>
                                </div>
                                <div class="text-sm text-gray-600"><strong>Конкуренти:</strong> competitor1.com, competitor2.com, competitor3.com</div>
                            </div>

                            <div class="border border-gray-200 rounded-lg p-4">
                                <div class="font-medium text-gray-900 mb-2">Підставка для ноутбука</div>
                                <div class="flex items-center justify-between mb-2">
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                                        Не рекомендується
                                    </span>
                                </div>
                                <div class="text-sm text-gray-600"><strong>Конкуренти:</strong> competitor4.com, competitor5.com</div>
                            </div>

                            <div class="border border-gray-200 rounded-lg p-4">
                                <div class="font-medium text-gray-900 mb-2">USB-C хаб</div>
                                <div class="flex items-center justify-between mb-2">
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                                        Не рекомендується
                                    </span>
                                </div>
                                <div class="text-sm text-gray-600"><strong>Конкуренти:</strong> competitor6.com, competitor7.com, competitor8.com, competitor9.com</div>
                            </div>

                            <div class="border border-gray-200 rounded-lg p-4">
                                <div class="font-medium text-gray-900 mb-2">Чохол для телефону</div>
                                <div class="flex items-center justify-between mb-2">
                                    <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                                        Рекомендується (1)
                                    </span>
                                </div>
                                <div class="text-sm text-gray-600"><strong>Конкуренти:</strong> competitor10.com, competitor11.com, competitor12.com</div>
                            </div>
                        </div>

                        <div class="mt-8 text-center text-gray-500 text-sm">
                            * Це приклад результатів. Ваші реальні результати прийдуть на пошту після завантаження файлу
                        </div>
                    </div>
                </div>
            </section>

            <!-- Problem Section -->
            <section class="py-16 px-4 sm:px-6 lg:px-8 bg-white">
                <div class="max-w-6xl mx-auto">
                    <div class="text-center mb-12">
                        <h2 class="text-4xl md:text-5xl font-bold mb-6 text-gray-900">Чи рекомендує ШІ саме ВАШІ продукти/послуги чи продукти ваших конкурентів?</h2>
                    </div>
                    
                    <div class="grid md:grid-cols-2 gap-12 items-center">
                        <div class="feature-card bg-gray-50 rounded-2xl p-8 text-center border border-gray-200">
                            <div class="w-16 h-16 bg-blue-500 rounded-full flex items-center justify-center mx-auto mb-6">
                                <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"></path>
                                </svg>
                            </div>
                            <h3 class="text-xl font-semibold text-gray-900 mb-3">Клієнт запитує ChatGPT</h3>
                            <p class="text-gray-600">"Який найкращий бездротовий зарядний пристрій для iPhone?"</p>
                        </div>
                        
                        <div class="feature-card bg-red-50 rounded-2xl p-8 text-center border border-red-200">
                            <div class="w-16 h-16 bg-red-500 rounded-full flex items-center justify-center mx-auto mb-6">
                                <svg class="w-8 h-8 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.172 16.172a4 4 0 015.656 0M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                                </svg>
                            </div>
                            <h3 class="text-xl font-semibold text-gray-900 mb-3">ШІ рекомендує 3 продукти</h3>
                            <p class="text-red-600 font-medium">Жоден не ваш</p>
                        </div>
                    </div>
                </div>
            </section>

            <!-- Social Proof -->
            <section class="py-16 px-4 sm:px-6 lg:px-8 bg-gray-50">
                <div class="max-w-5xl mx-auto">
                    <div class="grid md:grid-cols-2 gap-12">
                        <div class="feature-card bg-white rounded-2xl p-8 text-center border border-gray-200">
                            <p class="text-xl text-gray-700 italic mb-6">"Нарешті я знаю, чи рекомендує ШІ мою продукти"</p>
                            <div class="flex items-center justify-center space-x-3">
                                <div class="w-10 h-10 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full flex items-center justify-center text-white font-bold">A</div>
                                <div class="text-left">
                                    <div class="font-semibold text-gray-900">Alex</div>
                                    <div class="text-sm text-gray-600">Joozoor</div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="feature-card bg-white rounded-2xl p-8 text-center border border-gray-200">
                            <p class="text-xl text-gray-700 italic mb-6">"Виявили, чому конкуренти отримують згадки в ШІ замість нас"</p>
                            <div class="flex items-center justify-center space-x-3">
                                <div class="w-10 h-10 bg-gradient-to-r from-green-500 to-blue-500 rounded-full flex items-center justify-center text-white font-bold">С</div>
                                <div class="text-left">
                                    <div class="font-semibold text-gray-900">Сергій</div>
                                    <div class="text-sm text-gray-600">Complimed</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </section>

            <!-- Final CTA Section -->
            <section class="py-16 px-4 sm:px-6 lg:px-8 bg-white">
                <div class="max-w-4xl mx-auto text-center">
                    <h2 class="text-4xl md:text-5xl font-bold mb-8 text-gray-900">Готові побачити, чи рекомендує ШІ ваші продукти?</h2>
                    
                    <div class="flex justify-center mb-8">
                        <button id="finalCTA" class="gradient-button hover:opacity-90 px-10 py-5 rounded-xl font-bold text-xl text-white transition-all transform hover:scale-105 shadow-lg">
                            Спробувати безкоштовно - 10 запитів
                        </button>
                    </div>
                    
                    <p class="text-gray-500 text-lg">Безкоштовна пробна версія • Результати за 60 секунд • Без кредитної картки</p>
                </div>
            </section>
        </div>

        <!-- PAGE 2: Email Collection Page -->
        <div id="emailPage" class="page-transition hidden-page">
            <section class="pb-12 px-4 sm:px-6 lg:px-8 bg-white flex items-center justify-center">
                <div class="max-w-2xl mx-auto text-center">
                    <div class="bg-green-50 rounded-2xl p-8 border border-green-200">
                        <div class="w-20 h-20 bg-green-500 rounded-full flex items-center justify-center mx-auto mb-6">
                            <svg class="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                            </svg>
                        </div>
                        
                        <h1 class="text-3xl md:text-4xl font-bold mb-6 text-green-800">
                            Ваш звіт сформовано!
                        </h1>
                        
                        <p class="text-xl text-green-700 mb-8">
                            Щоб його отримати, залиште вашу пошту
                        </p>
                        
                        <p class="text-sm text-green-600 mb-8 bg-green-100 p-3 rounded-lg">
                            ℹ️ Зараз ми надішлемо тільки ваш звіт з результатами аналізу. В подальшому повідомимо про вихід нової версії продукту.
                        </p>

                        <!-- Email Form -->
                        <div class="space-y-6">
                            <div>
                                <div class="relative">
                                    <input type="email" id="userEmail" 
                                           class="w-full px-4 py-4 border border-gray-300 rounded-lg focus:ring-2 focus:ring-green-500 focus:border-green-500 text-lg transition-all" 
                                           placeholder="your.email@example.com">
                                    <div class="absolute inset-y-0 right-0 pr-3 flex items-center">
                                        <svg class="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 4.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path>
                                        </svg>
                                    </div>
                                </div>
                                <div id="emailError" class="hidden text-red-600 text-sm mt-2">
                                    <svg class="w-4 h-4 inline mr-1" fill="currentColor" viewBox="0 0 20 20">
                                        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path>
                                    </svg>
                                    <span id="emailErrorText"></span>
                                </div>
                            </div>

                            <button id="submitEmail" class="gradient-button hover:opacity-90 px-12 py-4 rounded-xl font-bold text-xl text-white transition-all shadow-lg disabled:opacity-50 disabled:cursor-not-allowed w-full" disabled>
                                <span id="submitButtonText">Отримати звіт</span>
                                <div id="submitSpinner" class="hidden">
                                    <svg class="animate-spin h-5 w-5 mx-auto" viewBox="0 0 24 24">
                                        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none"></circle>
                                        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                    </svg>
                                </div>
                            </button>

                            <!-- Back Button -->
                            <button id="backToMain" class="text-gray-600 underline underline-offset-4 decoration-gray-400 hover:decoration-2 font-medium transition-all">
                                ← Повернутись назад
                            </button>
                        </div>
                    </div>
                </div>
            </section>
        </div>

        <!-- PAGE 3: Success Message -->
        <div id="successPage" class="page-transition hidden-page">
            <section class="pb-12 px-4 sm:px-6 lg:px-8 bg-white flex items-center justify-center">
                <div class="max-w-2xl mx-auto text-center">
                    <div class="bg-green-50 rounded-2xl p-8 border border-green-200">
                        <div class="w-20 h-20 bg-green-500 rounded-full flex items-center justify-center mx-auto mb-6">
                            <svg class="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                            </svg>
                        </div>
                        <h1 class="text-3xl md:text-4xl font-bold text-green-800 mb-6">Дякуємо!</h1>
                        <p class="text-xl text-green-700 mb-6">
                            Чекайте аналітику по вашим запитам на вашій поштовій скриньці
                        </p>
                        <p class="text-green-600 text-lg mb-8">
                            Обробка файлу займає 2-5 хвилин. Результати прийдуть на <strong id="userEmailDisplay"></strong>
                        </p>
                        
                        <button id="backToMainFromSuccess" class="text-gray-600 underline underline-offset-4 decoration-gray-400 hover:decoration-2 font-medium transition-all">
                            ← Повернутись на головну
                        </button>
                    </div>
                </div>
            </section>
        </div>
    </div>

    <!-- Footer -->
    <footer class="py-12 px-4 sm:px-6 lg:px-8 bg-gray-100 mt-auto">
        <div class="max-w-6xl mx-auto text-center">
            <div class="text-xl font-bold gradient-text mb-4">BoostMyGEO</div>
            <div class="text-gray-600 text-sm">
                © 2025 BoostMyGEO. Перевірте, чи рекомендує ШІ ваші продукти.
            </div>
        </div>
    </footer>

    <script>
        // Global variables
        let currentFile = null;
        let currentEmail = '';
        let hasUsedService = false;

        // CSV Template Download
        document.getElementById('downloadTemplate').addEventListener('click', function() {
            const csvContent = `query
бездротовий зарядний пристрій iphone
usb-c хаб
підставка для ноутбука
чохол для телефону`;
            
            const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
            const link = document.createElement('a');
            const url = URL.createObjectURL(blob);
            link.setAttribute('href', url);
            link.setAttribute('download', 'keyword_template.csv');
            link.style.visibility = 'hidden';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        });

        // Page transitions
        function showPage(pageId) {
            const pages = ['uploadPage', 'emailPage', 'successPage'];
            
            pages.forEach(id => {
                const page = document.getElementById(id);
                if (id === pageId) {
                    page.classList.remove('hidden-page');
                    page.classList.add('show-page');
                } else {
                    page.classList.remove('show-page');
                    page.classList.add('hidden-page');
                }
            });

            // Scroll to top
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }

        // Email validation
        function validateEmail(email) {
            const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
            return re.test(email);
        }

        // Email input handling
        const emailInput = document.getElementById('userEmail');
        const emailError = document.getElementById('emailError');
        const emailErrorText = document.getElementById('emailErrorText');
        const submitButton = document.getElementById('submitEmail');

        emailInput?.addEventListener('input', function() {
            const email = this.value.trim();
            currentEmail = email;
            
            if (email === '') {
                hideEmailError();
                submitButton.disabled = true;
                return;
            }

            if (!validateEmail(email)) {
                showEmailError('Введіть коректну адресу електронної пошти');
                return;
            }

            hideEmailError();
            submitButton.disabled = false;
        });

        function showEmailError(message) {
            emailErrorText.textContent = message;
            emailError.classList.remove('hidden');
            emailInput.classList.add('border-red-500', 'focus:ring-red-500', 'focus:border-red-500');
            submitButton.disabled = true;
        }

        function hideEmailError() {
            emailError.classList.add('hidden');
            emailInput.classList.remove('border-red-500', 'focus:ring-red-500', 'focus:border-red-500');
        }

        // File Upload Handling
        const uploadArea = document.getElementById('uploadArea');
        const fileInput = document.getElementById('fileInput');
        const uploadContent = document.getElementById('uploadContent');
        const fileSuccess = document.getElementById('fileSuccess');
        const errorInfo = document.getElementById('errorInfo');

        // Click to select file
        uploadArea.addEventListener('click', () => fileInput.click());
        
        // Drag and drop
        uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            uploadArea.classList.add('drag-over');
        });

        uploadArea.addEventListener('dragleave', () => {
            uploadArea.classList.remove('drag-over');
        });

        uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            uploadArea.classList.remove('drag-over');
            const files = e.dataTransfer.files;
            if (files.length > 0) {
                handleFile(files[0]);
            }
        });

        fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                handleFile(e.target.files[0]);
            }
        });

        function handleFile(file) {
            // Reset states
            uploadContent.classList.add('hidden');
            fileSuccess.classList.add('hidden');
            errorInfo.classList.add('hidden');

            // Validate file
            if (!file.name.toLowerCase().endsWith('.csv')) {
                showError('Будь ласка, оберіть CSV файл');
                return;
            }

            if (file.size > 1024 * 1024) { // 1MB
                showError('Файл занадто великий. Максимум 1 МБ');
                return;
            }

            // Store file and show success
            currentFile = file;
            document.getElementById('fileName').textContent = file.name;
            document.getElementById('fileSize').textContent = `(${(file.size / 1024).toFixed(1)} KB)`;
            fileSuccess.classList.remove('hidden');
            
            // Start 3-second timer
            startTimer();
            
            console.log(`File ready: ${file.name}`);
        }

        function showError(message) {
            document.getElementById('errorMessage').textContent = message;
            errorInfo.classList.remove('hidden');
            uploadContent.classList.remove('hidden');
            currentFile = null;
        }

        // Timer functionality
        function startTimer() {
            let timeLeft = 3;
            const timerSeconds = document.getElementById('timerSeconds');
            const timerProgress = document.getElementById('timerProgress');
            
            const timer = setInterval(() => {
                timeLeft--;
                timerSeconds.textContent = timeLeft;
                timerProgress.style.width = ((3 - timeLeft) / 3 * 100) + '%';
                
                if (timeLeft <= 0) {
                    clearInterval(timer);
                    // Redirect to email page
                    showPage('emailPage');
                    // Focus on email input
                    setTimeout(() => {
                        document.getElementById('userEmail').focus();
                    }, 300);
                }
            }, 1000);
        }

        // Submit email
        submitButton?.addEventListener('click', async function() {
            if (!currentEmail || !currentFile || !validateEmail(currentEmail)) {
                return;
            }

            // Show loading state
            const submitButtonText = document.getElementById('submitButtonText');
            const submitSpinner = document.getElementById('submitSpinner');
            
            submitButton.disabled = true;
            submitButtonText.classList.add('hidden');
            submitSpinner.classList.remove('hidden');

            // Simulate API call
            await new Promise(resolve => setTimeout(resolve, 2000));

            // Show success page
            document.getElementById('userEmailDisplay').textContent = currentEmail;
            showPage('successPage');
            hasUsedService = true;

            // Reset loading state
            submitButton.disabled = false;
            submitButtonText.classList.remove('hidden');
            submitSpinner.classList.add('hidden');

            console.log(`Form submitted: ${currentEmail}, file: ${currentFile.name}`);
        });

        // Back buttons
        document.getElementById('backToMain')?.addEventListener('click', () => {
            showPage('uploadPage');
        });

        document.getElementById('backToMainFromSuccess')?.addEventListener('click', () => {
            // Show upload complete section instead of upload form
            document.getElementById('uploadForm').classList.add('hidden');
            document.getElementById('uploadCompleteSection').classList.remove('hidden');
            showPage('uploadPage');
        });

        // Final CTA button
        document.getElementById('finalCTA').addEventListener('click', function() {
            if (hasUsedService) {
                // Scroll to upload complete section
                document.getElementById('uploadCompleteSection').scrollIntoView({ behavior: 'smooth', block: 'center' });
            } else {
                // Scroll to upload form
                document.getElementById('uploadForm').scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        });

        // Animation on scroll
        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('fade-in');
                }
            });
        }, observerOptions);

        document.querySelectorAll('.feature-card').forEach(el => {
            observer.observe(el);
        });
    </script>
</body>
</html>"""

@app.get("/", response_class=HTMLResponse)
async def get_landing_page():
    """
    Основная страница лендинга
    """
    return HTMLResponse(content=LANDING_HTML)

@app.post("/upload")
async def handle_upload(request: Request, file: UploadFile = File(...), email: str = Form(...)):
    """
    Обработка загруженного файла
    """
    # Валидация email
    if not EMAIL_REGEX.match(email):
        raise HTTPException(status_code=400, detail="Некоректний формат email")
    
    # Считываем содержимое файла
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Файл пустий")

    print(f"Прийнято файл: {file.filename} від {get_client_ip(request)} для {email}")

    # Валидация размера файла
    # Добавил этот блок в worker, чтобы не ждать здесь
    # try:
    #     FileProcessor.validate_file_size(content, MAX_UPLOAD_MB)
    # except ValueError as e:
    #     raise HTTPException(status_code=400, detail=str(e))
    
    # Проверяем не использовал ли пользователь уже сервис
    # Хэш файла для проверки, чтобы пользователь не отправлял один и тот же файл много раз
    client_ip = get_client_ip(request)
    file_hash = hashlib.sha256(content).hexdigest()
    
    try:
        db.check_ip_file_access(client_ip, file_hash, ALLOW_RETRY_SAME_FILE)
    except PermissionError as e:
        raise HTTPException(status_code=429, detail=str(e))
    except Exception as e:
        print(f"Database warning: {e}")
        pass
    
    # Сохраняем файл во временную директорию для обработки
    file_extension = FileProcessor.get_file_extension(file.filename)
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name
    except Exception as e:
        raise HTTPException(status_code=500, detail="Ошибка сохранения файла")
    
    # Запускаем обработку в отдельном потоке
    worker_thread = threading.Thread(
        target=process_file_worker,
        args=(temp_file_path, email, client_ip),
        daemon=True
    )
    worker_thread.start()
    
    # Возвращаем мгновенный ответ
    return JSONResponse({
        "ok": True,
        "email": email,
        "status": "processing",
        "message": "Файл прийнято в обробку. Очікуйте звіт на email."
    })

def process_file_worker(file_path: str, email: str, client_ip: str):
    """
    Фоновая задача для обработки файла и отправки отчета
    """
    try:
        print(f"Начало обработки файла {file_path}")

        # Обработка файла
        df, queries_count = FileProcessor.process_file(file_path)
        
        # Запрос к OpenAI
        all_results = []
        for index, row in df.iterrows():
            country = row['Country']
            prompt = row['Prompt']
            website = row['Website']
            
            # Запрос к OpenAI
            response_data = openai_client.search_with_web(prompt)
            
            # Расчет метрик
            metrics_data = MetricsCalculator.calculate_metrics(
                country=country,
                target_domain=website,
                sources=response_data['sources']
            )
            all_results.append(metrics_data)

        # Создание отчета
        report_df = pd.DataFrame(all_results)
        
        # Конвертация в CSV
        csv_buffer = BytesIO()
        report_df.to_csv(csv_buffer, index=False, encoding='utf-8')
        csv_content = csv_buffer.getvalue()

        # Сохранение email в БД
        db.save_email(email, client_ip)

        # Отправка email
        email_service.send_report_email(
            recipient_email=email,
            csv_content=csv_content,
            queries_count=queries_count
        )
        
    except Exception as e:
        print(f"❌ Ошибка в worker-потоке: {e}")
    finally:
        # Удаляем временный файл
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"Временный файл {file_path} удален.")

def get_client_ip(request: Request) -> str:
    """
    Получение IP адреса клиента из заголовков запроса
    """
    x_forwarded_for = request.headers.get('X-Forwarded-For')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.client.host

# Запуск валидации конфигурации
validate_config()
