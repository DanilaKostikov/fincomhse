import gspread
import json
import requests
import time
import os
from dotenv import load_dotenv

load_dotenv()


def collect_info(url):
    try:
        response = requests.get(url)
        url = response.url
        cookies = response.cookies
        cookies_final = []
        for c in cookies:
            cookies_final.append(c.value)
        wuid = cookies_final[0]
        sessionid = cookies_final[1]
        split_url = url.split('/')
        owner_name = split_url[5]
        funding_id = split_url[6]
        url = f'https://www.tinkoff.ru/api/common/v1/cm/crowdfund/info?appName=paymentscfn&appVersion=3.3.2&origin=web%2Cib5' \
              f'%2Cplatform&sessionid={sessionid}.m1-prod-api-042&wuid={wuid}' \
              f'&nickname={owner_name}&crowdFundingId={funding_id}'

        info = requests.get(url)
        info = json.loads(info.text)
        info = info['payload']

        name = info['info']['name']
        name = name.lower()
        needs = info['info']['collectAmount']['value']
        collected = info['balance']['value']
        return name, needs, collected
    except:
        return None, None, None


if __name__ == '__main__':
    gc = gspread.service_account(filename='credentials.json')
    GOOGLE_KEY = os.getenv("GOOGLE_KEY")
    BOT_CREDENTIALS = os.getenv("BOT_CREDENTIALS")
    sh = gc.open_by_key(GOOGLE_KEY)
    worksheet = sh.sheet1
    current_time = time.time()
    changed = []
    res_previous = []
    chat_id = -1002057511006
    while True:
        gc = gspread.service_account(filename='credentials.json')
        sh = gc.open_by_key(GOOGLE_KEY)
        worksheet = sh.sheet1
        res_new = []

        res = worksheet.get_all_records()

        for i in range(len(res)):
            flag = True
            for column_name in res[0]:
                if not res[i][column_name] and res[i][column_name] != 0:
                    flag = False
            if flag:
                owner = res[i]['ФИО']
                sbor_name = res[i]['Название / цель']
                res_new.append(sbor_name)
                url = 'https://' + res[i]['Ссылка на сбор'] if not 'https://' in res[i]['Ссылка на сбор'] else res[i][
                    'Ссылка на сбор']
                committee = res[i]['Комитет']
                annotation = res[i]['Аннотация']
                goal = res[i]['Сумма сбора']
                end_date = res[i]['Срок конец']
                collected_old = res[i]['Собрано на данный момент']
                ended = res[i]['Сбор окончен']
                start = res[i]['Пост о начале']
                try:
                    name, needs, collected = collect_info(url)
                except:
                    name, needs, collected = None, None, None
                if (collected or collected == 0) and ended == 0:
                    left = goal - collected
                    if collected != collected_old:
                        flag = True
                        for j in range(len(changed)):
                            if changed[j]['Название / цель'] == sbor_name:
                                changed[j] = res[i]
                                changed[j]['Собрано на данный момент'] = collected
                                changed[j]['Осталось собрать'] = left
                                flag = False
                        if flag:
                            change = res[i]
                            change['Собрано на данный момент'] = collected
                            change['Осталось собрать'] = left
                            changed.append(change)
                    worksheet.update(values=[[collected]], range_name=f'J{i + 2}')
                    worksheet.update(values=[[left]], range_name=f'K{i + 2}')
                    if left <= 0 and ended == 0:
                        for j in range(len(changed)):
                            if changed[j]['Название / цель'] == sbor_name:
                                changed.pop(j)
                        check_url = res[i]['Ссылка на папку с чеками']
                        new_post = f'<b>{sbor_name.upper()}</b>\n{committee}, {owner}\n\n<u>Собрана полная сумма</u>: <i>{goal}</i> рублей\nС отчетом о тратах можно ознакомиться по ссылке:\n{check_url}\n\nОгромное всем спасибо!⭐️🎉🎊'
                        requests.get(
                            f'https://api.telegram.org/bot{BOT_CREDENTIALS}/sendMessage?chat_id={chat_id}&parse_mode=HTML&text={new_post}')
                        worksheet.update(values=[['1']], range_name=f'P{i + 2}')
                if sbor_name not in res_previous and ended == 0 and start == 0:
                    new_post = f'<b>{sbor_name.upper()}</b>\n{committee}, {owner}\n\n<i>{annotation}</i>\n\n<u>Цель собрать</u>: <i>{goal}</i> рублей\n<a href="{url}">Поддержать проект</a>\n\nДедлайн сбора {end_date}'
                    requests.get(
                        f'https://api.telegram.org/bot{BOT_CREDENTIALS}/sendMessage?chat_id={chat_id}&parse_mode=HTML&text={new_post}')
                    worksheet.update(values=[['1']], range_name=f'Q{i + 2}')
        res_previous = res_new
        diff = time.time() - current_time
        if diff >= 86400:
            current_time = time.time()
            for sbor in changed:
                url = 'https://' + sbor['Ссылка на сбор'] if not 'https://' in sbor['Ссылка на сбор'] else sbor[
                    'Ссылка на сбор']
                sbor_name = sbor['Название / цель']
                committee = sbor['Комитет']
                owner = sbor['ФИО']
                collected = sbor['Собрано на данный момент']
                goal = sbor['Сумма сбора']
                left = sbor['Осталось собрать']
                end_date = sbor['Срок конец']
                new_post = f'<b>{sbor_name.upper()}</b>\n{committee}, {owner}\n\n<u>Собрано</u>: <i>{collected}</i> из <i>{goal}</i> рублей\n<u>Осталось собрать</u>: <i>{left}</i> рублей\n<a href="{url}">Поддержать проект</a>\n\nДедлайн сбора {end_date}'
                response = requests.get(
                    f'https://api.telegram.org/bot{BOT_CREDENTIALS}/sendMessage?chat_id={chat_id}&parse_mode=HTML&text={new_post}')
            changed = []
        time.sleep(300)
