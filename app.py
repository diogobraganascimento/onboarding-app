from datetime import datetime
from pathlib import Path
import os
import sqlite3

from werkzeug.utils import secure_filename

import pandas as pd

from flask import (
    Flask,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)


BASE_DIR = Path(__file__).resolve().parent

TEMPLATES_PATH = BASE_DIR / 'templates'

STATIC_PATH = BASE_DIR / 'statics'

DATABASE_PATH = BASE_DIR / 'dados.db'

UPLOAD_FOLDER = BASE_DIR / 'uploads'


app = Flask(
    __name__,
    template_folder=str(TEMPLATES_PATH),
    static_folder=str(STATIC_PATH),
)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def conectar_banco():
    """sumary_line

    Keyword arguments:
    argument -- Nenhum argumento necessário
    Return: conexão SQLite ativa
    """

    return sqlite3.connect(DATABASE_PATH)


def atualizar_banco():
    """sumary_line

    Keyword arguments:
    argument -- Nenhum argumento necessário
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
            numero_chamado TEXT,
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

    cursor.execute(
        '''
        PRAGMA table_info(erros)
        '''
    )

    colunas = [
        coluna[1]
        for coluna in cursor.fetchall()
    ]

    if 'origem' not in colunas:

        cursor.execute(
            '''
            ALTER TABLE erros
            ADD COLUMN origem TEXT
            '''
        )

    if 'etapa' not in colunas:

        cursor.execute(
            '''
            ALTER TABLE erros
            ADD COLUMN etapa TEXT
            '''
        )

    if 'area_responsavel' not in colunas:

        cursor.execute(
            '''
            ALTER TABLE erros
            ADD COLUMN area_responsavel TEXT
            '''
        )

    if 'desvio_identificado' not in colunas:

        cursor.execute(
            '''
            ALTER TABLE erros
            ADD COLUMN desvio_identificado TEXT
            '''
        )

    if 'motivo' not in colunas:

        cursor.execute(
            '''
            ALTER TABLE erros
            ADD COLUMN motivo TEXT
            '''
        )

    conn.commit()

    conn.close()


def importar_planilha(caminho_arquivo):
    """sumary_line

    Keyword arguments:
    argument -- Caminho do arquivo Excel
    Return: None
    """

    df = pd.read_excel(caminho_arquivo)

    conn = conectar_banco()

    cursor = conn.cursor()

    for _, linha in df.iterrows():

        cursor.execute(
            '''
            INSERT INTO erros (
                data,
                site,
                numero_chamado,
                origem,
                etapa,
                area_responsavel,
                desvio_identificado,
                motivo
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                str(linha['Data']),
                str(linha['Site']),
                str(linha['Número']),
                str(linha['Origem']),
                str(linha['Etapa']),
                str(linha['Área Responsável']),
                str(linha['Desvio identificado']),
                str(linha['Motivo']),
            )
        )

    conn.commit()

    conn.close()


@app.route('/', methods=['GET', 'POST'])
def index():
    """sumary_line

    Keyword arguments:
    argument -- Requisição HTTP GET ou POST
    Return: Template HTML renderizado
    """

    conn = conectar_banco()

    cursor = conn.cursor()

    if request.method == 'POST':

        site = request.form['site']

        numero = request.form['numero']

        data = request.form['data']

        origem = request.form['origem']

        etapa = request.form['etapa']

        area_responsavel = request.form[
            'area_responsavel'
        ]

        motivo = request.form['motivo']

        desvio_identificado = request.form.get(
            'desvio_identificado'
        )

        novo_erro = request.form.get(
            'novo_erro'
        )

        if (
            not desvio_identificado
            and
            not novo_erro
        ):

            return redirect(
                url_for('index')
            )

        if novo_erro.strip():

            desvio_identificado = novo_erro.strip()

            try:

                cursor.execute(
                    '''
                    INSERT INTO tipos_erro (nome)
                    VALUES (?)
                    ''',
                    (desvio_identificado,)
                )

                conn.commit()

            except sqlite3.IntegrityError:

                pass

        cursor.execute(
            '''
            INSERT INTO erros (
                data,
                site,
                numero_chamado,
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
    argument -- Filtros de mês e site
    Return: Template HTML renderizado
    """

    mes = request.args.get('mes')

    site = request.args.get('site')

    conn = conectar_banco()

    cursor = conn.cursor()

    query = '''
        SELECT
            data,
            site,
            numero_chamado,
            origem,
            etapa,
            area_responsavel,
            desvio_identificado,
            motivo
        FROM erros
        WHERE 1=1
    '''

    params = []

    if mes:

        query += '''
            AND strftime('%m', data) = ?
        '''

        params.append(mes)

    if site:

        query += '''
            AND site = ?
        '''

        params.append(site)

    query += '''
        ORDER BY data DESC
    '''

    cursor.execute(query, params)

    dados = cursor.fetchall()

    query_grafico = '''
        SELECT
            desvio_identificado,
            COUNT(*) as total
        FROM erros
        WHERE 1=1
    '''

    params_grafico = []

    if mes:

        query_grafico += '''
            AND strftime('%m', data) = ?
        '''

        params_grafico.append(mes)

    if site:

        query_grafico += '''
            AND site = ?
        '''

        params_grafico.append(site)

    query_grafico += '''
        GROUP BY desvio_identificado
        ORDER BY total DESC
    '''

    cursor.execute(
        query_grafico,
        params_grafico,
    )

    grafico = cursor.fetchall()

    conn.close()

    total_registros = sum(
        item[1]
        for item in grafico
    )

    labels = []

    valores = []

    for item in grafico:

        erro = item[0]

        quantidade = item[1]

        porcentagem = round(
            (quantidade / total_registros) * 100,
            1,
        ) if total_registros > 0 else 0

        labels.append(
            f'{erro} ({porcentagem}%)'
        )

        valores.append(quantidade)

    return render_template(
        'relatorio.html',
        dados=dados,
        labels=labels,
        valores=valores,
        mes=mes,
        site=site,
    )


@app.route('/export')
def exportar_excel():
    """sumary_line

    Keyword arguments:
    argument -- Nenhum argumento necessário
    Return: Arquivo Excel para download
    """

    conn = conectar_banco()

    query = '''
        SELECT
            data AS "Data",
            site AS "Site",
            numero_chamado AS "Número",
            origem AS "Origem",
            etapa AS "Etapa",
            area_responsavel AS "Área Responsável",
            desvio_identificado AS "Desvio identificado",
            motivo AS "Motivo"
        FROM erros
        ORDER BY data DESC
    '''

    df = pd.read_sql_query(query, conn)

    conn.close()

    nome_arquivo = (
        f'relatorio_erros_'
        f'{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    )

    with pd.ExcelWriter(
        nome_arquivo,
        engine='openpyxl',
    ) as writer:

        df.to_excel(
            writer,
            index=False,
            sheet_name='Detalhes1',
        )

    return send_file(
        nome_arquivo,
        as_attachment=True,
    )


@app.route('/importar', methods=['POST'])
def importar_excel():
    """sumary_line

    Keyword arguments:
    argument -- Arquivo enviado via formulário
    Return: Redirecionamento para relatório
    """

    arquivo = request.files.get('arquivo')

    if not arquivo:

        return redirect(
            url_for('relatorio')
        )

    os.makedirs(
        app.config['UPLOAD_FOLDER'],
        exist_ok=True,
    )

    nome_arquivo = secure_filename(
        arquivo.filename
    )

    caminho_arquivo = (
        app.config['UPLOAD_FOLDER'] / nome_arquivo
    )

    arquivo.save(caminho_arquivo)

    importar_planilha(caminho_arquivo)

    return redirect(
        url_for('relatorio')
    )


# =========================================================
# INÍCIO BLOCO TEMPORÁRIO PARA TESTES
# ESTE TRECHO SERÁ REMOVIDO APÓS FINALIZAÇÃO DOS TESTES
# =========================================================

@app.route('/limpar-dados', methods=['POST'])
def limpar_dados():
    """sumary_line

    Keyword arguments:
    argument -- Requisição HTTP POST
    Return: Redirecionamento para relatório
    """

    conn = conectar_banco()

    cursor = conn.cursor()

    cursor.execute('DELETE FROM erros')

    conn.commit()

    conn.close()

    arquivos = os.listdir(BASE_DIR)

    for arquivo in arquivos:

        if (
            arquivo.startswith('relatorio_erros_')
            and arquivo.endswith('.xlsx')
        ):

            os.remove(BASE_DIR / arquivo)

    return redirect(
        url_for('relatorio')
    )

# =========================================================
# FIM BLOCO TEMPORÁRIO PARA TESTES
# =========================================================


if __name__ == '__main__':

    atualizar_banco()

    app.run(debug=True)