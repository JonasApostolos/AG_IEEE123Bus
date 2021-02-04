import win32com.client
import py_dss_interface
from win32com.client import makepy
from pylab import *
from operator import itemgetter
import random
import os
import csv
import numpy
import statistics

class DSS(object):  # Classe DSS
    def __init__(self, dssFileName):
        self.dss = py_dss_interface.DSSDLL()
        self.dssFileName = dssFileName

    def compile_DSS(self):
        self.dss.dss_clearall()

        self.dss.text("compile [{}]".format(self.dssFileName))
        # OpenDSS folder
        self.OpenDSS_folder_path = os.path.dirname(self.dssFileName)

    def solve(self, solucao, kWRatedList):
        # self.compile_DSS()
        self.results_path = self.OpenDSS_folder_path + "/results_Main"
        self.dss.text("set DataPath=" + self.results_path)

        # Monitores
        listaCargas = self.listaCargas()
        for i in listaCargas:
            self.dss.text("New Monitor." + str(listaCargas.index(i)) + " Element=" + i + " mode=32 terminal=1")

        # PmppList = list(range(100, 4700, 200))
        LoadshapePointsList = [round(ctd, 2) for ctd in list(numpy.arange(-1.0, 1.05, 0.05))]
        Loadshape = [LoadshapePointsList[ctd] for ctd in solucao[1:]]
        Loadshape = self.LoadshapeToMediaMovel(Loadshape)
        # print(Loadshape)

        self.dss.text("Loadshape.Loadshape1.mult=" + str(Loadshape))
        self.dss.text("Storage.storage.Bus1=" + '60')
        # self.dss.text("PVSystem.PV.Bus1=" + '107139M3009 ')
        self.dss.text("Storage.storage.kWrated=" + str(kWRatedList[solucao[0]]))
        self.dss.text("Storage.storage.kva=" + str(kWRatedList[solucao[0]]))
        self.dss.text("Storage.storage.kw=" + str(kWRatedList[solucao[0]]))
        # self.dss.text("Storage.storage.kWrated=1000")
        # self.dss.text("Storage.storage.kva=1000")
        # self.dss.text("Storage.storage.kw=1000")
        # self.dss.text("PVSystem.PV.KVA=" + '2500')
        # self.dss.text("PVSystem.PV.Pmpp=" + '2500')
        self.dss.text("Storage.storage.enabled=yes")

        self.dss.text("Solve")

        self.dss.text("export meters")
        self.dss.text("export monitor Potencia_Feeder")
        self.dss.text("export monitor Storage")


        for i in listaCargas:
            self.dss.text("export monitor " + str(listaCargas.index(i)))

    def funcaoCusto(self, solucao, kWRatedList):
        self.compile_DSS()
        self.solve(solucao, kWRatedList)

        # Inclinaçoes
        Inclinacao = 0
        ListaInclinacoes = self.InclinacoesLoadshape(solucao)

        for i in ListaInclinacoes:
            if numpy.abs(i) > 40:
                Inclinacao += numpy.abs(i)

        # Punição Niveis de Tensão
        if self.BarrasTensaoVioladas() > self.BarrasTensaoVioladasOriginal:
            PunicaoTensao = 9999999999
        else:
            PunicaoTensao = 0

        # PESOS
        a = 0.5  # Perdas
        b = 0.5  # DP do Carregamento do trafo

        # CICLO DE CARGA DA BATERIA
        # É preciso garantir que ao final das 48h o nível de carregamento da bateria seja o mesmo do inicio da simulacao
        dataMonitorStorage = {}

        fname = "D:\\UFBA/IC-storage\\AG_IEEE123Bus\\123Bus\\results_Main\\ieee123_Mon_storage_1.csv"

        with open(str(fname), 'r', newline='') as file:
            csv_reader_object = csv.reader(file)
            name_col = next(csv_reader_object)
            for row in name_col:
                dataMonitorStorage[row] = []
            for row in csv_reader_object:  ##Varendo todas as linhas
                for ndata in range(0, len(name_col)-2):  ## Varendo todas as colunas
                    rowdata = row[ndata].replace(" ", "").replace('"',"")
                    dataMonitorStorage[name_col[ndata]].append(float(rowdata))

        Carregamento48h = dataMonitorStorage[' kWh'][-1]
        PunicaoCicloCarga = pow(abs((30000-Carregamento48h)/1000),1.5)

        # PERDAS
        ### Acessando arquivo CSV Potência
        dataEnergymeterCSV = {}
        self.dataperda = {}

        fname = "D:\\UFBA/IC-storage\\AG_IEEE123Bus\\123Bus\\results_Main\\ieee123_EXP_METERS.csv"

        with open(str(fname), 'r', newline='') as file:
            csv_reader_object = csv.reader(file)
            name_col = next(csv_reader_object)

            for row in name_col:
                dataEnergymeterCSV[row] = []

            for row in csv_reader_object:  ##Varendo todas as linhas
                for ndata in range(0, len(name_col)):  ## Varendo todas as colunas
                    rowdata = row[ndata].replace(" ", "").replace('"',"")
                    if rowdata == "FEEDER" or rowdata == "":
                        dataEnergymeterCSV[name_col[ndata]].append(rowdata)
                    else:
                        dataEnergymeterCSV[name_col[ndata]].append(float(rowdata))

        self.dataperda['Perdas %'] = (dataEnergymeterCSV[' "Zone Losses kWh"'][0]/dataEnergymeterCSV[' "Zone kWh"'][0])*100
        os.remove(fname)

        # DESVIO PADRÃO DO CARREGAMENTO DO TRAFO
        ### Acessando arquivo CSV Potência
        dataFeederMmonitorCSV = {}

        fname = "D:\\UFBA/IC-storage\\AG_IEEE123Bus\\123Bus\\results_Main\\ieee123_Mon_potencia_feeder_1.csv"

        with open(str(fname), 'r', newline='') as file:
            csv_reader_object = csv.reader(file)
            name_col = next(csv_reader_object)

            for row in name_col:
                dataFeederMmonitorCSV[row] = []

            dataFeederMmonitorCSV['PTotal'] = []

            for row in csv_reader_object:  ##Varendo todas as linhas
                Pt = 0
                for ndata in range(0, len(name_col)):  ## Varendo todas as colunas
                    rowdata = row[ndata].replace(" ", "").replace('"',"")
                    dataFeederMmonitorCSV[name_col[ndata]].append(float(rowdata))
                    if name_col[ndata] == ' P1 (kW)' or name_col[ndata] == ' P2 (kW)' or name_col[ndata] == ' P3 (kW)':
                        Pt += float(rowdata)

                dataFeederMmonitorCSV['PTotal'].append(Pt)
        Desvio = statistics.pstdev(dataFeederMmonitorCSV['PTotal'])
        Perdas_sem_Pv_Stor = 2.316

        #Custo = a/(Perdas_sem_Pv_Stor/100-self.dataperda['Perdas %']/100) + b*Desvio + Inclinacao + PunicaoTensao + PunicaoCicloCarga
        Custo = 1/self.dataperda['Perdas %']/100 + b*Desvio + PunicaoTensao + Inclinacao + PunicaoTensao + PunicaoCicloCarga
        return Custo

    def mutacao(self, dominio, passo, solucao):
        i = random.randint(0, len(dominio) - 1)
        mutante = solucao

        if random.random() < 0.5:
            if solucao[i] != dominio[i][0] and solucao[i] >= (dominio[i][0] + passo):
                mutante = solucao[0:i] + [solucao[i] - passo] + solucao[i + 1:]
        else:
            if solucao[i] != dominio[i][1] and solucao[i] <= (dominio[i][1] - passo):
                mutante = solucao[0:i] + [solucao[i] + passo] + solucao[i + 1:]

        return mutante

    def cruzamento(self, dominio, individuo1, individuo2):
        i = random.randint(1, len(dominio) - 2)
        return individuo1[0:i] + individuo2[i:]

    def genetico(self, kWRatedList, dominio, tamanho_populacao=80,  passo=1,
                 probabilidade_mutacao=0.2, elitismo=0.2, numero_geracoes=300):

        self.Cenario() # cria o cenario

        self.BarrasTensaoVioladasOriginal = self.CalculaCustosOriginal()

        populacao = []
        LoadshapePointsList = [round(ctd, 2) for ctd in list(numpy.arange(-1.0, 1.05, 0.05))]
        listadeLoadShapes1 = [
            [0, 0, -0.3, -0.45, -0.5, -0.45, -0.3, 0, 0, 0, 0, 0, 0, 0, 0, 0.3, 0.5, 0.8, 0.9, 0.8, 0.5, 0.3, 0, 0],
            [0, 0, -0.3, -0.45, -0.5, -0.45, -0.3, 0, 0, 0, 0, 0, 0, 0, 0, 0.3, 0.4, 0.6, 0.8, 0.9, 0.8, 0.5, 0.3, 0],
            [0, 0, 0, -0.3, -0.45, -0.5, -0.45, -0.3, 0, 0, 0, 0, 0, 0, 0, 0, 0.3, 0.6, 0.75, 0.95, 0.9, 0.8, 0.3, 0],
            [0, -0.1, -0.2, -0.2, -0.2, -0.2, -0.2, -0.2, -0.1, 0, 0, 0, 0, 0, 0.3, 0.6, 0.8, 0.8, 0.8, 0.6, 0.4, 0, 0,
             0],
            [0.3, 0.3, 0.3, 0.3, 0.3, 0.2, 0.1, 0, 0, -0.5, -0.6, -0.7, -0.8, -0.9, -0.9, -0.8, -0.4, 0.3, 0.5, 0.8,
             0.9, 0.7, 0.3, 0.3],
            [0, -0.1, -0.2, -0.2, 0, 0, 0, 0, -0.1, -0.3, -0.65, -0.7, -0.8, -0.9, -0.85, -0.75, -0.45, 0.5, 0.9, 0.9,
             0.95, 0.8, 0.8, 0.7],
            [0.3, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0, -0.1, -0.3, -0.6, -0.75, -0.75, -0.8, -0.9, -0.85, -0.4, 0.5, 0.9,
             0.9, 0.9, 0.8, 0.8, 0.7],
            [0.3, 0.3, 0.5, 0.5, 0.5, 0.3, 0.3, 0.3, 0, 0, -0.8, -0.8, -0.9, -0.9, -0.8, -0.8, -0.8, 0, 0.75, 0.8, 0.9,
             0.8, 0.8, 0.4],
            [0.2, 0.25, 0.15, 0.2, 0.2, 0.2, 0.65, 0.7, 0.7, -0.3, -0.65, -0.65, -0.75, -0.85, -0.95, -0.95, -0.45,
             0.45, 0.85, 0.85, 0.85, 0.85, 0.7, 0.35],
            [0.15, 0.15, 0.15, 0, 0, 0, 0, 0, -0.05, -0.05, -0.45, -0.45, -0.75, -0.75, -0.75, -0.75, -0.75, -0.75, 0.3,
             0.45, 0.55, 0.5, 0.5, 0.05],
            [0.05, 0, 0, 0, 0, 0, 0, 0, -0.1, -0.25, -0.35, -0.55, -0.6, -0.9, -0.9, -0.95, -0.5, 0.45, 0.75, 0.85, 0.9,
             0.9, 0.75, 0.15],
            [0.05, 0.45, 0.75, 0.75, 0.75, 0.75, 0.75, 0.15, 0, 0, -0.35, -0.35, -0.95, -0.95, -0.95, -0.95, -0.4, 0.45,
             0.55, 0.6, 0.6, 0.6, 0.6, 0.15],
            [0.1, -0.2, -0.2, -0.2, -0.2, 0, 0, 0, -0.1, -0.25, -0.4, -0.6, -0.6, -0.6, -0.6, -0.5, -0.4, 0.6, 0.8, 0.9,
             0.8, 0.5, 0.3, 0],
            [-0.15, -0.15, -0.15, -0.15, 0, 0, 0, 0, 0, -0.2, -0.4, -0.5, -0.7, -0.7, -0.5, -0.4, -0.2, 0.45, 0.75, 0.8,
             0.75, 0.75, 0.5, -0.25],
            [0.2, 0.25, 0.2, 0.25, 0.2, 0.25, 0.2, 0.25, -0.2, -0.25, -0.6, -0.6, -0.7, -0.8, -0.8, -0.8, -0.6, 0.45,
             0.9, 0.95, 0.95, 0.9, 0.75, 0.1],
            [0, 0.05, 0.1, 0.15, 0.15, 0, 0, 0, -0.1, -0.3, -0.4, -0.6, -0.7, -0.75, -0.85, -0.8, -0.8, 0.25, 0.5, 0.7,
             0.7, 0.9, 0.3, 0.1],
            [-0.3, -0.3, -0.3, -0.3, -0.3, -0.05, -0.05, -0.05, -0.1, -0.15, -0.3, -0.3, -0.5, -0.55, -0.55, -0.65,
             -0.5, 0.25, 0.5, 0.9, 0.9, 0.9, 0.5, 0.4],
            [-0.25, -0.3, -0.25, -0.3, -0.25, -0.3, 0, 0, 0, -0.35, -0.55, -0.65, -0.7, -0.75, -0.95, -0.4, -0.3, 0.2,
             0.5, 0.85, 0.8, 0.85, 0.5, 0.4],
            [0.1, 0.1, 0.1, 0.1, 0.2, 0.35, 0.35, 0.45, 0.1, -0.3, -0.5, -0.7, -0.75, -0.85, -0.85, -0.85, -0.75, -0.15,
             0.7, 0.75, 0.75, 0.75, 0.3, 0.25],
            [0.3, 0.3, 0.3, 0.3, 0.3, 0.45, 0.45, 0.45, 0.15, -0.2, -0.5, -0.65, -0.75, -0.8, -0.85, -0.85, -0.8, -0.25,
             0.5, 0.8, 0.85, 0.85, 0.5, 0.2],
            [0.3, 0.3, 0.3, 0.3, 0.3, 0.45, 0.45, 0.45, 0.15, -0.3, -0.4, -0.6, -0.7, -0.75, -0.85, -0.8, -0.8, 0.25,
             0.5, 0.9, 0.9, 0.9, 0.6, 0.4],
            [0.35, 0.35, 0, 0, 0, 0.4, 0.45, 0.45, 0.15, -0.3, -0.55, -0.65, -0.7, -0.75, -0.85, -0.8, -0.8, 0.25, 0.5,
             0.9, 0.9, 0.9, 0.6, 0.4],
            [0.3, 0.15, 0.15, 0.15, 0.3, 0.4, 0.45, 0.45, 0.15, -0.3, -0.4, -0.6, -0.75, -0.75, -0.85, -0.8, -0.8, 0.25,
             0.45, 0.8, 0.9, 0.95, 0.6, 0.4],
            [0.3, 0.2, 0, 0, 0.1, 0.15, 0.15, 0.15, 0.15, -0.3, -0.4, -0.6, -0.7, -0.95, -0.95, -0.8, -0.8, 0.25, 0.45,
             0.9, 0.9, 0.9, 0.6, 0.4],
            [0.1, 0.15, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, -0.7, -0.7, -0.85, -0.85, -0.85, -0.3, 0.25, 0.5,
             0.6, 0.8, 0.85, 0.7, 0.4],
            [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, -0.5, -0.5, -0.5, -0.5, -0.5, -0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0]
        ]
        listadeLoadShapes2 = [
            [-0.3,-0.3,-0.3,-0.3,-0.3,-0.3,-0.3,0,0.3,0.45,0.5,0.5,0.45,0.3,0.1,-0.1,-0.1,-0.1,-0.1,-0.1,-0.1,-0.1,-0.1,-0.1],
            [-0.3,-0.45,-0.5,-0.45,-0.3,0,0,0,0,0,0,0,0,0,0,0.3,0.4,0.6,0.8,0.9,0.8,0.5,0.3,0],
            [0,0,0,-0.3,-0.45,-0.5,-0.45,-0.3,0,0,0,0,0,0,0,0,0.3,0.6,0.75,0.95,0.9,0.8,0.3,0],
            [0,0,0,0,0,0,0,0,0,0,0,-0.5,-0.5,-0.5,-0.5,-0.5,-0.5,0.5,0.5,0.5,0.5,0.5,0.5,0],
            [0.1,0.1,0.1,0.1,0.1,0.1,0.1,0,-0.1,-0.3,-0.6,-0.75,-0.75,-0.8,-0.9,-0.85,-0.4,0.5,0.9,0.9,0.9,0.8,0.8,0.7],
            [0,0.3,0.4,0.6,0.7,0.6,0.4,0.3,0,-0.3,-0.45,-0.5,-0.45,-0.4,-0.3,-0.05,0.25,0.4,0.55,0.6,0.6,0.45,0.25,0.15],
            [0.4,0.4,0.4,0.4,0.4,0.4,0.4,0.4,0.4,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0.05,0.05,0.05,0.05,0.05,0.05,0.05,0.05,0.05,-0.3,-0.3,-0.3,-0.3,-0.3,-0.3,-0.3,-0.3,0.05,0.05,0.05,0.05,0.05,0.05,0.05],
            [0.15,0.15,0.15,0.15,0.15,0.15,0.15,0.15,0.15,0.15,0.15,0,0,0,0,0,0,-0.35,-0.35,-0.35,-0.35,-0.35,-0.35,-0.35],
            [-0.2,-0.2,-0.2,-0.2,-0.2,-0.2,-0.2,-0.2,-0.2,-0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.2,0.4,0.4,0.4,0.4,0.4,0.4]
        ]

        # Cria a primeira geração
        for i in range(tamanho_populacao):
            # Solucao para todos os valores Random
            solucao = []
            for ctd in range(len(dominio)):
                if ctd == 0 or ctd == 1:
                    solucao.append(random.randint(dominio[ctd][0], dominio[ctd][1]))
                else:
                    a = [dominio[ctd][0], solucao[-1] - 14]
                    a = max(a)
                    b = [dominio[ctd][1], solucao[-1] + 14]
                    b = min(b)
                    solucao.append(random.randint(a, b))
            # solucao = [random.randint(dominio[i][0], dominio[i][1]) for i in range(len(dominio))]
            # print(solucao)
            populacao.append(solucao)

        numero_elitismo = int(elitismo * tamanho_populacao)
        geracao = 1
        stop = False
        melhor_solucao = [] # Lista de menor custo por geracao

        while stop == False:
            start = time.time()
            custos = [(self.funcaoCusto(individuo, kWRatedList), individuo) for individuo in populacao]
            custos.sort()
            melhor_solucao.append(custos[0][0])
            if melhor_solucao.count(custos[0][0]) == int(0.2*tamanho_populacao):
                stop = True
            # custos_traduzidos = [(ctd[0], kWRatedList[ctd[1][0]], [LoadshapePointsList[i] for i in ctd[1][1:]]) for ctd in custos]
            custos_traduzidos = [(ctd[0], kWRatedList[ctd[1][0]]) for ctd in custos]
            print("Geração::", geracao,  custos_traduzidos)
            self.CalculaCustos(custos[0][1], kWRatedList)
            print("Melhores Resultados", melhor_solucao)
            geracao += 1
            individuos_ordenados = [individuo for (custo, individuo) in custos]
            populacao = individuos_ordenados[0:numero_elitismo]
            lista_rank = [(individuo, (tamanho_populacao - individuos_ordenados.index(individuo))/(tamanho_populacao*(tamanho_populacao-1))) for individuo in individuos_ordenados]
            lista_rank.reverse()
            soma=0
            for ctd in lista_rank:
                soma += ctd[1]

            # Cruzamento e Mutacao dos individuos
            while len(populacao) < tamanho_populacao:
                if random.random() < probabilidade_mutacao:
                    m = random.randint(0, numero_elitismo)
                    populacao.append(self.mutacao(dominio, passo, individuos_ordenados[m]))
                else:
                    aleatorio = random.uniform(0, soma)
                    # print('aleatorio', aleatorio)
                    s = 0
                    for j in lista_rank:
                        s += j[1]
                        if aleatorio < s:
                            c1 = j[0]
                            # print('c1', c1)
                            break
                    aleatorio = random.uniform(0, soma)
                    s = 0
                    for j in lista_rank:
                        s += j[1]
                        if aleatorio < s:
                            c2 = j[0]
                            # print('c2', c2)
                            break
                    populacao.append(self.cruzamento(dominio, c1, c2))
                    # c1 = random.randint(0, numero_elitismo)
                    # c2 = random.randint(0, numero_elitismo)
                    # populacao.append(self.cruzamento(dominio, individuos_ordenados[c1], individuos_ordenados[c2]))

            end = time.time()
            print("Tempo da geração:", end - start)
        return custos[0][1]

    def listaCargas(self):
        dataCargasDSS = []
        for linha in open('D:\\UFBA/IC-storage\\AG_IEEE123Bus\\123Bus\\IEEE123Loads.DSS'):
            if linha.split(" ")[0] != "!" and linha.split(" ")[0] != "Redirect":
                dataCargasDSS.append(linha.split(" ")[1])
        return dataCargasDSS

    def LoadshapeToMediaMovel(self, solucao):
        medias_moveis = []
        num_media = 2
        i = 0
        while i < (len(solucao) - num_media + 1):
            grupo = solucao[i: i + num_media]
            media_grupo = sum(grupo) / num_media
            medias_moveis.append(media_grupo)
            i += 1
        medias_moveis.insert(0, medias_moveis[0])
        return medias_moveis

    def InclinacoesLoadshape(self, solucao):
        LoadshapePointsList = [round(ctd, 2) for ctd in list(numpy.arange(-1.0, 1.05, 0.05))]
        Loadshape = [LoadshapePointsList[i] for i in solucao[1:]]
        Inclinacoes = []

        for i in range((len(Loadshape)-1)):
            x = Loadshape[i+1] - Loadshape[i]
            Inclinacoes.append(numpy.arctan(x)*180/pi)

        return Inclinacoes

    def BarrasTensaoVioladas(self):
        BarrasVioladas = 0
        listaCargas = self.listaCargas()

        for i in listaCargas:
            dataMonitorCargas = {}
            fname = "D:\\UFBA/IC-storage\\AG_IEEE123Bus\\123Bus\\results_Main\\ieee123_Mon_" + str(listaCargas.index(i)) + "_1.csv"

            with open(str(fname), 'r', newline='') as file:
                csv_reader_object = csv.reader(file)
                name_col = next(csv_reader_object)

                for row in name_col:
                    dataMonitorCargas[row] = []

                for row in csv_reader_object:  ##Varendo todas as linhas
                    for ndata in range(0, len(name_col)):  ## Varendo todas as colunas
                        rowdata = row[ndata].replace(" ", "").replace('"',"")
                        if name_col[ndata] == ' |V|1 (volts)' or name_col[ndata] == ' |V|2 (volts)' or name_col[ndata] == ' |V|3 (volts)':
                            dataMonitorCargas[name_col[ndata]].append(float(rowdata)/127)

            TensaoPUFasesBarras = dataMonitorCargas[' |V|1 (volts)'] + dataMonitorCargas[' |V|2 (volts)']
            # print(TensaoPUFasesBarras)
            for ctd in TensaoPUFasesBarras:
                if ctd > 1.03 or ctd < 0.97:
                    BarrasVioladas += 1

        # TensaoPUFasesBarras = d.dssCircuit.AllNodeVmagPUByPhase(1) + d.dssCircuit.AllNodeVmagPUByPhase(2) + d.dssCircuit.AllNodeVmagPUByPhase(3)
        # for i in TensaoPUFasesBarras:
        #     if i > 1.03 or i < 0.97:
        #         BarrasVioladas += 1
        return BarrasVioladas

    def Cenario(self, porcentagem_prosumidores=0.4):
        self.compile_DSS()
        self.dss.text("Storage.storage.enabled=no")

        self.dss.text("Solve")

        pv_file = open("PVSystems.dss", "w")
        # Cargas e Barras
        loadlist = []
        loaddict = {}
        for load in self.dss.loads_allnames():
            self.dss.loads_write_name(load)
            kvbase = self.dss.loads_read_kv()
            numphases = self.dss.cktelement_numphases()
            bus = str(self.dss.cktelement_read_busnames()).replace("'", "").replace('(', "").replace(')', "").replace(',',"")
            curva = self.dss.loads_read_daily()
            self.dss.loadshapes_write_name(curva)
            Epv = 7.89*0.97**2 # capacidade de geracao
            Ec = 0 # consumo diario medio
            for i in self.dss.loadshapes_read_pmult():
                Ec += i * 0.25
            pmpp = round(Ec / Epv, 2)
            loaddict[load] = [numphases, bus, kvbase, pmpp]

            loadlist.append((Ec,load))
        loadlist.sort(reverse=True)
        # print('loadlist', loadlist)

        # Seleção por Roleta dos Prosumidores
        fim = round(len(loadlist) * porcentagem_prosumidores)
        # print('fim', fim)

        prosumidores = []
        while len(prosumidores) < fim:
            soma = 0
            for ctd in loadlist:
                soma += ctd[0]
            # print(soma)

            aleatorio = random.uniform(0, soma)
            # print('aleatorio', aleatorio)
            s = 0
            for j in loadlist:
                s += j[0]
                if aleatorio < s:
                    prosumidor = j
                    # print('prosumidor', prosumidor)
                    break
            prosumidores.append(prosumidor[1])
            loadlist.remove(prosumidor)

        print('Prosumidores', prosumidores)

        # Inserindo os PVsystems
        ctd = 0
        for load in prosumidores:
            pv_file.write(f"New PVSystem.PV{ctd} phases={loaddict[load][0]} Bus1={loaddict[load][1]} kV={loaddict[load][2]} kVA={loaddict[load][3]} Pmpp={loaddict[load][3]} conn=wye PF = 1 %cutin = 0.00005 %cutout = 0.00005 effcurve = Myeff P-TCurve = MyPvsT Daily = MyIrrad TDaily = Mytemp \n")
            ctd += 1
        pv_file.close()

    def CalculaCustos(self, solucao, kWRatedList):
        self.compile_DSS()
        self.solve(solucao, kWRatedList)

        LoadshapePointsList = [round(ctd, 2) for ctd in list(numpy.arange(-1.0, 1.05, 0.05))]
        Loadshape = [LoadshapePointsList[ctd] for ctd in solucao[1:]]

        # CICLO DE CARGA DA BATERIA
        # É preciso garantir que ao final das 48h o nível de carregamento da bateria seja o mesmo do inicio da simulacao
        dataMonitorStorage = {}

        fname = "D:\\UFBA/IC-storage\\AG_IEEE123Bus\\123Bus\\results_Main\\ieee123_Mon_storage_1.csv"

        with open(str(fname), 'r', newline='') as file:
            csv_reader_object = csv.reader(file)
            name_col = next(csv_reader_object)
            for row in name_col:
                dataMonitorStorage[row] = []
            for row in csv_reader_object:  ##Varendo todas as linhas
                for ndata in range(0, len(name_col)-2):  ## Varendo todas as colunas
                    rowdata = row[ndata].replace(" ", "").replace('"',"")
                    dataMonitorStorage[name_col[ndata]].append(float(rowdata))

        Carregamento48h = dataMonitorStorage[' kWh'][-1]
        PunicaoCicloCarga = pow(abs((30000-Carregamento48h)/1000),1.5)

        # Inclinaçoes
        Inclinacao = 0
        ListaInclinacoes = self.InclinacoesLoadshape(solucao)

        for i in ListaInclinacoes:
            if numpy.abs(i) > 40:
                Inclinacao += numpy.abs(i)

        ### Acessando arquivo CSV Potência
        dataEnergymeterCSV = {}
        self.dataperda = {}

        fname = "D:\\UFBA/IC-storage\\AG_IEEE123Bus\\123Bus\\results_Main\\ieee123_EXP_METERS.csv"


        with open(str(fname), 'r', newline='') as file:
            csv_reader_object = csv.reader(file)
            name_col = next(csv_reader_object)

            for row in name_col:
                dataEnergymeterCSV[row] = []

            for row in csv_reader_object:  ##Varendo todas as linhas
                for ndata in range(0, len(name_col)):  ## Varendo todas as colunas
                    rowdata = row[ndata].replace(" ", "").replace('"',"")
                    if rowdata == "FEEDER" or rowdata == "":
                        dataEnergymeterCSV[name_col[ndata]].append(rowdata)
                    else:
                        dataEnergymeterCSV[name_col[ndata]].append(float(rowdata))

        self.dataperda['Perdas %'] = (dataEnergymeterCSV[' "Zone Losses kWh"'][0]/dataEnergymeterCSV[' "Zone kWh"'][0])*100
        os.remove(fname)

        ### Acessando arquivo CSV Potência
        dataFeederMmonitorCSV = {}

        fname = "D:\\UFBA/IC-storage\\AG_IEEE123Bus\\123Bus\\results_Main\\ieee123_Mon_potencia_feeder_1.csv"

        with open(str(fname), 'r', newline='') as file:
            csv_reader_object = csv.reader(file)
            name_col = next(csv_reader_object)

            for row in name_col:
                dataFeederMmonitorCSV[row] = []

            dataFeederMmonitorCSV['PTotal'] = []

            for row in csv_reader_object:  ##Varendo todas as linhas
                Pt = 0
                for ndata in range(0, len(name_col)):  ## Varendo todas as colunas
                    rowdata = row[ndata].replace(" ", "").replace('"', "")
                    dataFeederMmonitorCSV[name_col[ndata]].append(float(rowdata))
                    if name_col[ndata] == ' P1 (kW)' or name_col[ndata] == ' P2 (kW)' or name_col[ndata] == ' P3 (kW)':
                        Pt += float(rowdata)

                dataFeederMmonitorCSV['PTotal'].append(Pt)

        print('Perdas:', self.dataperda['Perdas %'], 'kWh 48h:', Carregamento48h, 'Inclinação:', Inclinacao, 'Barras_Violada:', self.BarrasTensaoVioladas(), 'PTotal:', dataFeederMmonitorCSV['PTotal'])
        print('Loadshape:', self.LoadshapeToMediaMovel(Loadshape))

    def CalculaCustosOriginal(self):
        self.compile_DSS()

        self.results_path = self.OpenDSS_folder_path + "/results_Main"
        self.dss.text("set DataPath=" + self.results_path)

        # Monitores
        listaCargas = self.listaCargas()
        for i in listaCargas:
            self.dss.text("New Monitor." + str(listaCargas.index(i)) + " Element=" + i + " mode=32 terminal=1")

        self.dss.text("Storage.storage.enabled=no")

        self.dss.text("Solve")

        self.dss.text("export meters")
        self.dss.text("export monitor Potencia_Feeder")

        for i in listaCargas:
            self.dss.text("export monitor " + str(listaCargas.index(i)))

        ### Acessando arquivo CSV Potência
        dataEnergymeterCSV = {}
        self.dataperda = {}

        fname = "D:\\UFBA/IC-storage\\AG_IEEE123Bus\\123Bus\\results_Main\\ieee123_EXP_METERS.csv"


        with open(str(fname), 'r', newline='') as file:
            csv_reader_object = csv.reader(file)
            name_col = next(csv_reader_object)

            for row in name_col:
                dataEnergymeterCSV[row] = []

            for row in csv_reader_object:  ##Varendo todas as linhas
                for ndata in range(0, len(name_col)):  ## Varendo todas as colunas
                    rowdata = row[ndata].replace(" ", "").replace('"',"")
                    if rowdata == "FEEDER" or rowdata == "":
                        dataEnergymeterCSV[name_col[ndata]].append(rowdata)
                    else:
                        dataEnergymeterCSV[name_col[ndata]].append(float(rowdata))

        self.dataperda['Perdas %'] = (dataEnergymeterCSV[' "Zone Losses kWh"'][0]/dataEnergymeterCSV[' "Zone kWh"'][0])*100
        os.remove(fname)

        ### Acessando arquivo CSV Potência
        dataFeederMmonitorCSV = {}

        fname = "D:\\UFBA/IC-storage\\AG_IEEE123Bus\\123Bus\\results_Main\\ieee123_Mon_potencia_feeder_1.csv"

        with open(str(fname), 'r', newline='') as file:
            csv_reader_object = csv.reader(file)
            name_col = next(csv_reader_object)

            for row in name_col:
                dataFeederMmonitorCSV[row] = []

            dataFeederMmonitorCSV['PTotal'] = []

            for row in csv_reader_object:  ##Varendo todas as linhas
                Pt = 0
                for ndata in range(0, len(name_col)):  ## Varendo todas as colunas
                    rowdata = row[ndata].replace(" ", "").replace('"', "")
                    dataFeederMmonitorCSV[name_col[ndata]].append(float(rowdata))
                    if name_col[ndata] == ' P1 (kW)' or name_col[ndata] == ' P2 (kW)' or name_col[ndata] == ' P3 (kW)':
                        Pt += float(rowdata)

                dataFeederMmonitorCSV['PTotal'].append(Pt)

        barrasVioladas = self.BarrasTensaoVioladas()
        print('Custos Sistema Original (Somente GD-PV)')
        print('Perdas:', self.dataperda['Perdas %'], 'Violações de Tensao:', barrasVioladas, 'PTotal:', dataFeederMmonitorCSV['PTotal'], '\n')
        return barrasVioladas





if __name__ == '__main__':
    d = DSS(r"D:\\UFBA/IC-storage\\AG_IEEE123Bus\\123Bus\\Run_IEEE123Bus.dss")
    kWRatedList = list(range(100, 5100, 100))
    dominio = [(0, len(kWRatedList) - 1), (0, 40) , (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40)]
    # dominio = [(0, 40) , (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40)]


    solucao_genetico = d.genetico(kWRatedList, dominio)
    custo_genetico = d.funcaoCusto(solucao_genetico, kWRatedList)
    print(custo_genetico)
    print(solucao_genetico)
