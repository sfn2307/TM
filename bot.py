from flask import Flask
from threading import Thread
import logging
import os
import time
import asyncio
import requests
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler
from dotenv import load_dotenv

app = Flask(__name__)

@app.route("/")
def hello():
    return "Bot is running!"

def run_flask():
    app.run(host="0.0.0.0", port=80)

if __name__ == '__main__':
    flask_thread = Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    load_dotenv()
    BOT_TOKEN = os.getenv('BOT_TOKEN')
    CHAT_ID = os.getenv('CHAT_ID')
    URLS = [
        'https://www.kmu.gov.ua/timeline?type=posts',
        'https://me.gov.ua/InfoRez/List/7758c77b-e410-44ea-a07d-37f1799e11e5?tag=ZapitiKoristuvachiv&lang=uk-UA&pageNumber=1&fCtx=inRequest&fCtx2=inRequest&fAndOrNot=and&sortCtx=date',
        'https://www.kmu.gov.ua/npasearch?&from=27.01.2025',
        'https://dasu.gov.ua/ua/newslist?rubric=1',
        'https://rp.gov.ua/PressCenter/News/',
        'https://amcu.gov.ua/napryami/oskarzhennya-publichnih-zakupivel/komisia-z-rozglyadu-skarg/uzagalnena-praktika-kolegiyi-amku-z-oskarzhennya-publichnih-zakupivel/uzahalnena-praktyka-komisii-amku-za-2025',
        'https://amcu.gov.ua/timeline?&type=posts',
        'https://radnuk.com.ua/novyny/',
        'https://tndr.com.ua',
        'https://prozorro.gov.ua/uk/news',
        'https://blog.zakupivli.pro',
        'https://e-tender.ua/novini?type=4',
        'https://news.dzo.com.ua/category/novini/',
        'https://infobox.prozorro.org'
    ]
    LAST_DOCUMENTS_DIR = 'last_documents/'
    logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
    logger = logging.getLogger(__name__)
    if not os.path.exists(LAST_DOCUMENTS_DIR):
        os.makedirs(LAST_DOCUMENTS_DIR)

    def fetch_documents(url):
        try:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            document_list = soup.find_all('a')
            documents = []
            for item in document_list:
                title = item.get_text(strip=True)
                link = item.get('href')
                if title and link:
                    documents.append({'title': title, 'link': link, 'date': 'не вказано'})
            return documents
        except requests.exceptions.RequestException as e:
            logger.error(f"Помилка при отриманні сторінки {url}: {e}")
            return None
        except Exception as e:
            logger.error(f"Помилка при парсингу сторінки {url}: {e}")
            return None

    def load_last_documents(url):
        site_name = url.split('//')[1].split('/')[0]
        file_path = os.path.join(LAST_DOCUMENTS_DIR, f'{site_name}_last_documents.txt')
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f]
        return []

    def save_last_documents(url, documents):
        site_name = url.split('//')[1].split('/')[0]
        file_path = os.path.join(LAST_DOCUMENTS_DIR, f'{site_name}_last_documents.txt')
        with open(file_path, 'w', encoding='utf-8') as f:
            for doc in documents:
                f.write(f"{doc['title']}\n")

    async def check_for_new_documents(context):
        logger.info("Перевірка на нові документи...")
        for url in URLS:
            logger.info(f"Перевірка сайту: {url}")
            documents = fetch_documents(url)
            if documents:
                last_documents = load_last_documents(url)
                new_documents = [doc for doc in documents if doc['title'] not in last_documents]
                if new_documents:
                    message = f"З'явилися нові документи на сайті {url}:\n\n"
                    for doc in new_documents:
                        message += f"📄 <a href='{doc['link']}'>{doc['title']}</a> ({doc['date']})\n"
                    message += "\nПереглянути повний список: " + url
                    try:
                        await context.bot.send_message(
                            chat_id=CHAT_ID,
                            text=message,
                            parse_mode=telegram.ParseMode.HTML,
                            disable_web_page_preview=True
                        )
                        save_last_documents(url, documents)
                        logger.info(f"Надіслано сповіщення про {len(new_documents)} нових документів для {url}.")
                    except Exception as e:
                        logger.error(f"Помилка при відправці повідомлення: {e}")
                else:
                    logger.info(f"Нових документів на сайті {url} не знайдено.")
            else:
                logger.error(f"Не вдалося отримати список документів з сайту {url}.")

    async def start(update: Update, context):
        await update.message.reply_text('Бот запущено та готовий до роботи!')
        await check_for_new_documents(context)

    def main():
        application = Application.builder().token(BOT_TOKEN).build()
        application.add_handler(CommandHandler("start", start))

        async def periodic_check(context):
            await check_for_new_documents(context)

        job_queue = application.job_queue
        job_queue.run_repeating(periodic_check, interval=3600, first=10) # Перевірка кожну годину

        application.run_polling()

    main()
