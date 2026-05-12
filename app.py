# app.py

from datetime import datetime
from pathlib import Path
import math
import os
import sqlite3

import pandas as pd

from flask import (
    Flask,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)

from werkzeug.utils import secure_filename


BASE_DIR = Path(__file__).resolve().parent

TEMPLATES_PATH = BASE_DIR / 'templates'

STATIC_PATH = BASE_DIR / 'statics'

DATABASE_PATH = BASE_DIR / 'dados.db'

UPLOAD_FOLDER = BASE_DIR / 'uploads'

REGISTROS_POR_PAGINA = 25


app = Flask(
    __name__,
    template_folder=str(TEMPLATES_PATH),
    static_folder=str(STATIC_PATH),
)

app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)


def conectar_banco():
    """sumary_line

    Keyword arguments:
    argument -- conexão SQLite
    Return: conexão ativa
    """

    return sqlite3.connect(DATABASE_PATH)


def atualizar_banco():
    """sumary_line

    Keyword arguments:
    argument -- criação das tabelas
    Return: None
    """

    conn = conectar_banco()

    cursor = conn.cursor()

    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS erros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT,
            site TEXT,
            numero TEXT,
            origem TEXT,
            etapa TEXT,
            area_responsavel TEXT,
            desvio_identificado TEXT,
            motivo TEXT
        )
        '''
    )

    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS tipos_erro (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE
        )
        '''
    )

    conn.commit()

    conn.close()


@app.route('/', methods=['GET', 'POST'])
def index():
    """sumary_line

    Keyword arguments:
    argument -- renderização index
    Return: template index.html
    """

    conn = conectar_banco()

    cursor = conn.cursor()

    if request.method == 'POST':

        data = request.form['data']

        site = request.form['site']

        numero = request.form['numero']

        origem = request.form['origem']

        etapa = request.form['etapa']

        area_responsavel = request.form[
            'area_responsavel'
        ]

        motivo = request.form['motivo']

        desvio_existente = request.form.get(
            'desvio_identificado'
        )

        novo_desvio = request.form.get(
            'novo_desvio'
        )

        if novo_desvio and novo_desvio.strip():

            desvio_identificado = (
                novo_desvio.strip()
            )

            try:

                cursor.execute(
                    '''
                    INSERT INTO tipos_erro (
                        nome
                    )
                    VALUES (?)
                    ''',
                    (desvio_identificado,)
                )

                conn.commit()

            except sqlite3.IntegrityError:

                pass

        else:

            desvio_identificado = (
                desvio_existente
            )

        cursor.execute(
            '''
            INSERT INTO erros (
                data,
                site,
                numero,
                origem,
                etapa,
                area_responsavel,
                desvio_identificado,
                motivo
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                data,
                site,
                numero,
                origem,
                etapa,
                area_responsavel,
                desvio_identificado,
                motivo,
            )
        )

        conn.commit()

        return redirect(
            url_for('index')
        )

    cursor.execute(
        '''
        SELECT nome
        FROM tipos_erro
        ORDER BY nome ASC
        '''
    )

    erros = cursor.fetchall()

    conn.close()

    return render_template(
        'index.html',
        erros=erros,
    )


@app.route('/relatorio')
def relatorio():
    """sumary_line

    Keyword arguments:
    argument -- filtros relatório
    Return: template relatorio.html
    """

    pagina = request.args.get(
        'pagina',
        1,
        type=int
    )

    mes = request.args.get('mes', '')

    site = request.args.get('site', '')

    desvio = request.args.get('desvio', '')

    grafico_erros = request.args.get(
        'grafico_erros',
        'bar'
    )

    grafico_areas = request.args.get(
        'grafico_areas',
        'bar'
    )

    conn = conectar_banco()

    cursor = conn.cursor()

    query_base = '''
        FROM erros
        WHERE 1=1
    '''

    params = []

    if mes:

        query_base += '''
            AND strftime('%m', data) = ?
        '''

        params.append(mes)

    if site:

        query_base += '''
            AND site = ?
        '''

        params.append(site)

    if desvio:

        query_base += '''
            AND desvio_identificado = ?
        '''

        params.append(desvio)

    cursor.execute(
        f'''
        SELECT COUNT(*)
        {query_base}
        ''',
        params,
    )

    total_registros = cursor.fetchone()[0]

    total_paginas = math.ceil(
        total_registros / REGISTROS_POR_PAGINA
    )

    offset = (
        pagina - 1
    ) * REGISTROS_POR_PAGINA

    query_dados = f'''
        SELECT
            data,
            site,
            numero,
            origem,
            etapa,
            area_responsavel,
            desvio_identificado,
            motivo
        {query_base}
        ORDER BY data DESC
        LIMIT ? OFFSET ?
    '''

    params_dados = (
        params +
        [
            REGISTROS_POR_PAGINA,
            offset,
        ]
    )

    cursor.execute(
        query_dados,
        params_dados,
    )

    dados = cursor.fetchall()

    query_erros = f'''
        SELECT
            desvio_identificado,
            COUNT(*) as total
        {query_base}
        GROUP BY desvio_identificado
        ORDER BY total DESC
    '''

    cursor.execute(
        query_erros,
        params,
    )

    grafico_erros_dados = cursor.fetchall()

    labels = []

    valores = []

    total_erros = sum(
        item[1]
        for item in grafico_erros_dados
    )

    for item in grafico_erros_dados:

        labels.append(item[0])

        percentual = round(
            (
                item[1] / total_erros
            ) * 100,
            1
        ) if total_erros > 0 else 0

        valores.append(percentual)

    query_areas = f'''
        SELECT
            area_responsavel,
            COUNT(*) as total
        {query_base}
        GROUP BY area_responsavel
        ORDER BY total DESC
    '''

    cursor.execute(
        query_areas,
        params,
    )

    grafico_areas_dados = cursor.fetchall()

    labels_area = []

    valores_area_percentual = []

    total_areas = sum(
        item[1]
        for item in grafico_areas_dados
    )

    for item in grafico_areas_dados:

        labels_area.append(item[0])

        percentual = round(
            (
                item[1] / total_areas
            ) * 100,
            1
        ) if total_areas > 0 else 0

        valores_area_percentual.append(
            percentual
        )

    cursor.execute(
        '''
        SELECT DISTINCT site
        FROM erros
        ORDER BY site ASC
        '''
    )

    lista_sites = [
        item[0]
        for item in cursor.fetchall()
    ]

    cursor.execute(
        '''
        SELECT DISTINCT desvio_identificado
        FROM erros
        ORDER BY desvio_identificado ASC
        '''
    )

    lista_desvios = [
        item[0]
        for item in cursor.fetchall()
    ]

    conn.close()

    return render_template(
        'relatorio.html',
        dados=dados,
        labels=labels,
        valores=valores,
        labels_area=labels_area,
        valores_area_percentual=valores_area_percentual,
        lista_sites=lista_sites,
        lista_desvios=lista_desvios,
        pagina=pagina,
        total_paginas=total_paginas,
        mes=mes,
        site=site,
        desvio=desvio,
        grafico_erros=grafico_erros,
        grafico_areas=grafico_areas,
    )

if __name__ == '__main__':

    atualizar_banco()

    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
    )

