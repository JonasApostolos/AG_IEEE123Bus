
import win32com.client
from win32com.client import makepy
from pylab import *
from operator import itemgetter
import random
import os
import csv
import numpy

class DSS(object):  # Classe DSS
    def __init__(self, dssFileName):

        # Create a new instance of the DSS
        sys.argv = ["makepy", "OpenDSSEngine.DSS"]
        makepy.main()
        self.dssObj = win32com.client.Dispatch("OpenDSSEngine.DSS")

        # Start the DSS
        if self.dssObj.Start(0) == False:
            print("DSS Failed to Start")
        else:
            self.dssFileName = dssFileName
            # Assign a variable to each of the interfaces for easier access
            self.dssText = self.dssObj.Text
            self.dssCircuit = self.dssObj.ActiveCircuit
            self.dssSolution = self.dssCircuit.Solution
            self.dssCktElement = self.dssCircuit.ActiveCktElement
            self.dssBus = self.dssCircuit.ActiveBus
            self.dssTransformer = self.dssCircuit.Transformers

    def compile_DSS(self):
        # Always a good idea to clear the DSS when loading a new circuit
        # self.dssObj.ClearAll()

        # Load the given circuit master file into OpenDSS
        self.dssText.Command = "compile " + self.dssFileName

        # OpenDSS folder
        self.OpenDSS_folder_path = os.path.dirname(self.dssFileName)

    def solve(self, solucao):
        # self.compile_DSS()
        self.results_path = self.OpenDSS_folder_path + "/results_Main"
        self.dssText.Command = "set DataPath=" + self.results_path

        kWRatedList = list(range(100, 3100, 100))
        # PmppList = list(range(100, 4700, 200))
        LoadshapePointsList = [round(ctd, 2) for ctd in list(numpy.arange(-1.0, 1.05, 0.05))]
        Loadshape = [LoadshapePointsList[ctd] for ctd in solucao[1:]]
        # print(Loadshape)

        self.dssText.Command = "Loadshape.Loadshape1.mult=" + str(Loadshape)
        self.dssText.Command = "Storage.storage.Bus1=" + '60'
        self.dssText.Command = "PVSystem.PV.Bus1=" + '60'
        # self.dssText.Command = "Storage.storage.kWrated=" + str(kWRatedList[solucao[0]])
        # self.dssText.Command = "Storage.storage.kva=" + str(kWRatedList[solucao[0]])
        # self.dssText.Command = "Storage.storage.kw=" + str(kWRatedList[solucao[0]])
        self.dssText.Command = "Storage.storage.kWrated=600"
        self.dssText.Command = "Storage.storage.kva=600"
        self.dssText.Command = "Storage.storage.kw=600"
        self.dssText.Command = "PVSystem.PV.KVA=" + '2000'
        self.dssText.Command = "PVSystem.PV.Pmpp=" + '2000'

        self.dssSolution.Solve()

        self.dssText.Command = "export meters"
        # self.dssText.Command = "show eventlog"

    def funcaoCusto(self, solucao):
        # d = DSS(r"D:\UFBA\IC-storage\Algoritmo_Genetico\Main_ModoFollow_Trafo.F21898.dss")
        self.compile_DSS()
        self.solve(solucao)

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
        # print(self.dataperda['Perdas %'])
        return self.dataperda['Perdas %']

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

    def genetico(self, dominio, tamanho_populacao=50,  passo=4,
                 probabilidade_mutacao=0.2, elitismo=0.3, numero_geracoes=100):

        populacao = []
        kWRatedList = list(range(100, 3100, 100))
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

        for i in range(tamanho_populacao):
            # solucao = [random.randint(dominio[i][0], dominio[i][1]) for i in range(len(dominio) - 24)]
            Loadshape = [LoadshapePointsList.index(ctd) for ctd in listadeLoadShapes2[random.randint(0, 9)]]
            # solucao = solucao + Loadshape
            solucao = Loadshape

            # solucao = solucao + listadeLoadShapes[i]
            # print(solucao)
            populacao.append(solucao)

        numero_elitismo = int(elitismo * tamanho_populacao)
        geracao = 1

        for i in range(numero_geracoes):
            custos = [(self.funcaoCusto(individuo), individuo) for individuo in populacao]
            custos.sort()
            # custos_traduzidos = [(ctd[0], kWRatedList[ctd[1][0]], [LoadshapePointsList[i] for i in ctd[1][1:]]) for ctd in custos]
            custos_traduzidos = [(ctd[0], [LoadshapePointsList[i] for i in ctd[1][:]]) for ctd in custos]
            print("custos", geracao,  custos_traduzidos)
            geracao += 1
            individuos_ordenados = [individuo for (custo, individuo) in custos]
            populacao = individuos_ordenados[0:numero_elitismo]
            lista_rank = [(individuo, (tamanho_populacao - individuos_ordenados.index(individuo))/(tamanho_populacao*(tamanho_populacao-1))) for individuo in individuos_ordenados]
            lista_rank.reverse()
            # print("lista_rank", lista_rank)
            soma=0
            for ctd in lista_rank:
                soma += ctd[1]

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
        return custos[0][1]


if __name__ == '__main__':
    d = DSS(r"D:\\UFBA/IC-storage\\AG_IEEE123Bus\\123Bus\\Run_IEEE123Bus.dss")
    kWRatedList = list(range(100, 3100, 100))
    # dominio = [(0, len(kWRatedList) - 1), (0, 40) , (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40)]
    dominio = [(0, 40) , (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40)]


    solucao_genetico = d.genetico(dominio)
    custo_genetico = d.funcaoCusto(solucao_genetico)
    print(custo_genetico)
    print(solucao_genetico)

import win32com.client
from win32com.client import makepy
from pylab import *
from operator import itemgetter
import random
import os
import csv
import numpy

class DSS(object):  # Classe DSS
    def __init__(self, dssFileName):

        # Create a new instance of the DSS
        sys.argv = ["makepy", "OpenDSSEngine.DSS"]
        makepy.main()
        self.dssObj = win32com.client.Dispatch("OpenDSSEngine.DSS")

        # Start the DSS
        if self.dssObj.Start(0) == False:
            print("DSS Failed to Start")
        else:
            self.dssFileName = dssFileName
            # Assign a variable to each of the interfaces for easier access
            self.dssText = self.dssObj.Text
            self.dssCircuit = self.dssObj.ActiveCircuit
            self.dssSolution = self.dssCircuit.Solution
            self.dssCktElement = self.dssCircuit.ActiveCktElement
            self.dssBus = self.dssCircuit.ActiveBus
            self.dssTransformer = self.dssCircuit.Transformers

    def compile_DSS(self):
        # Always a good idea to clear the DSS when loading a new circuit
        # self.dssObj.ClearAll()

        # Load the given circuit master file into OpenDSS
        self.dssText.Command = "compile " + self.dssFileName

        # OpenDSS folder
        self.OpenDSS_folder_path = os.path.dirname(self.dssFileName)

    def solve(self, solucao):
        # self.compile_DSS()
        self.results_path = self.OpenDSS_folder_path + "/results_Main"
        self.dssText.Command = "set DataPath=" + self.results_path

        kWRatedList = list(range(100, 3100, 100))
        # PmppList = list(range(100, 4700, 200))
        LoadshapePointsList = [round(ctd, 2) for ctd in list(numpy.arange(-1.0, 1.05, 0.05))]
        Loadshape = [LoadshapePointsList[ctd] for ctd in solucao[1:]]
        # print(Loadshape)

        self.dssText.Command = "Loadshape.Loadshape1.mult=" + str(Loadshape)
        self.dssText.Command = "Storage.storage.Bus1=" + '60'
        self.dssText.Command = "PVSystem.PV.Bus1=" + '60'
        # self.dssText.Command = "Storage.storage.kWrated=" + str(kWRatedList[solucao[0]])
        # self.dssText.Command = "Storage.storage.kva=" + str(kWRatedList[solucao[0]])
        # self.dssText.Command = "Storage.storage.kw=" + str(kWRatedList[solucao[0]])
        self.dssText.Command = "Storage.storage.kWrated=600"
        self.dssText.Command = "Storage.storage.kva=600"
        self.dssText.Command = "Storage.storage.kw=600"
        self.dssText.Command = "PVSystem.PV.KVA=" + '2000'
        self.dssText.Command = "PVSystem.PV.Pmpp=" + '2000'

        self.dssSolution.Solve()

        self.dssText.Command = "export meters"
        # self.dssText.Command = "show eventlog"

    def funcaoCusto(self, solucao):
        # d = DSS(r"D:\UFBA\IC-storage\Algoritmo_Genetico\Main_ModoFollow_Trafo.F21898.dss")
        self.compile_DSS()
        self.solve(solucao)

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
        # print(self.dataperda['Perdas %'])
        return self.dataperda['Perdas %']

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

    def genetico(self, dominio, tamanho_populacao=50,  passo=1,
                 probabilidade_mutacao=0.2, elitismo=0.3, numero_geracoes=100):

        populacao = []
        kWRatedList = list(range(100, 3100, 100))
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

        for i in range(tamanho_populacao):
            # solucao = [random.randint(dominio[i][0], dominio[i][1]) for i in range(len(dominio) - 24)]
            Loadshape = [LoadshapePointsList.index(ctd) for ctd in listadeLoadShapes2[random.randint(0, 9)]]
            # solucao = solucao + Loadshape
            solucao = Loadshape

            # solucao = solucao + listadeLoadShapes[i]
            # print(solucao)
            populacao.append(solucao)

        numero_elitismo = int(elitismo * tamanho_populacao)
        geracao = 1

        for i in range(numero_geracoes):
            custos = [(self.funcaoCusto(individuo), individuo) for individuo in populacao]
            custos.sort()
            # custos_traduzidos = [(ctd[0], kWRatedList[ctd[1][0]], [LoadshapePointsList[i] for i in ctd[1][1:]]) for ctd in custos]
            custos_traduzidos = [(ctd[0], [LoadshapePointsList[i] for i in ctd[1][:]]) for ctd in custos]
            print("custos", geracao,  custos_traduzidos)
            geracao += 1
            individuos_ordenados = [individuo for (custo, individuo) in custos]
            populacao = individuos_ordenados[0:numero_elitismo]
            lista_rank = [(individuo, (tamanho_populacao - individuos_ordenados.index(individuo))/(tamanho_populacao*(tamanho_populacao-1))) for individuo in individuos_ordenados]
            lista_rank.reverse()
            # print("lista_rank", lista_rank)
            soma=0
            for ctd in lista_rank:
                soma += ctd[1]

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
        return custos[0][1]


if __name__ == '__main__':
    d = DSS(r"D:\\UFBA/IC-storage\\AG_IEEE123Bus\\123Bus\\Run_IEEE123Bus.dss")
    kWRatedList = list(range(100, 3100, 100))
    # dominio = [(0, len(kWRatedList) - 1), (0, 40) , (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40)]
    dominio = [(0, 40) , (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40),  (0, 40)]


    solucao_genetico = d.genetico(dominio)
    custo_genetico = d.funcaoCusto(solucao_genetico)
    print(custo_genetico)
    print(solucao_genetico)
