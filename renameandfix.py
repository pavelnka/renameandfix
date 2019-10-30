#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
#==============================================================================
#      LICENCIA
#------------------------------------------------------------------------------
#      Copyright 2008 (c) Pavel Ancka <pavelancka@gmail.com>
#
#      This program is free software; you can redistribute it and/or modify
#      it under the terms of the GNU General Public License as published by
#      the Free Software Foundation; either version 3 of the License, or
#      (at your option) any later version.
#
#      This program is distributed in the hope that it will be useful,
#      but WITHOUT ANY WARRANTY; without even the implied warranty of
#      MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#      GNU General Public License for more details.
#
#      You should have received a copy of the GNU General Public License
#      along with this program;
#                               <http://www.gnu.org/licenses/gpl.html>
#      If not, write to the Free Software Foundation, Inc., 51 Franklin
#      Street, Fifth Floor, Boston, MA 02110-1301, USA.
#==============================================================================
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.realpath(__file__))))
#------------------------------------------------------------------------------
import signal
import tty, termios
import select
import argparse
import re
from time import sleep
from unicodedata import normalize

class FuncionComun(object):
    
    #Reduce un textos con caracteres repetivos a un caracter: 'aaaa' -> 'a'
    @staticmethod
    def reduce(Texto):
        if len(Texto) > 1 and Texto.count(Texto[0]) == len(Texto):
            Texto = Texto[0]
        return(Texto)

    @staticmethod
    def CrearLista(Valor=None):
        if type(Valor) in (list, tuple) and len(Valor) > 0:
            return list(Valor)
        elif type(Valor) is str and len(Valor) > 0:
            return [Valor, ]
        else:
            return list()
    
    @staticmethod
    def inputs(Texto=str(), TiempoDeEspera=180):
    
        def WaitingTimeIsOver(SignalNumber, CurrentStackFrame):
            raise TimeoutError
    
        signal.signal(signal.SIGALRM, WaitingTimeIsOver)
        signal.alarm(TiempoDeEspera)  # 3 min = 180 segundos
        try:
            #FALTA SALIR CON LA TECLA ESC, ahora no funciona ESC solo produce '^['
            Texto = input(Texto)
        except:
            Texto = None
        signal.alarm(0)          # Es importante Deshabilitar la Alarma
        return(Texto)
    
    @staticmethod
    def ObtenerNombreyExtension(NombreArchivo):
        # 1. Quitar Extensiones dobles: filename.jpg.jpg
        # 2. Reconocer Extensiones dobles validas: filename.tar.gz
        DobleExtension = ('tar', 'gz', 'gzip', 'rar', 'bz2')
        nombre = NombreArchivo
        FullExt = str()
        while True:
            NombreArchivo = nombre
            nombre, ext = os.path.splitext(str(nombre))
            # ext = '.jpg'  --> pero puede ser ext = '.' ??
            if len(ext) > 0 and len(ext) < 6: # and ext != '.':
                ext = ext[1:].lower()
                if ext in DobleExtension:
                    if FullExt in DobleExtension:
                        if ext != FullExt:
                            FullExt = '{}.{}'.format(ext, FullExt)
                            NombreArchivo = nombre
                            break
                        else:
                            pass
                    elif len(FullExt) == 0:
                        FullExt = ext
                    else:
                        break
                else:
                    if len(FullExt) == 0:
                        FullExt = ext
                    elif FullExt != ext:
                        break
            if FullExt != ext or len(ext) == 0:
                break
        
        return(NombreArchivo, FullExt)
    
    #------------------------------------------------------------------------------
    @staticmethod
    def GetOptionKeys(Texto=str(), Opciones=list(), TiempoDeEspera=10, NumChar=1):
    
        #...Establecer Alarma................................................
        def SeAcaboElTiempoDeEspera(signum, frame):
            raise TimeoutError
        signal.signal(signal.SIGALRM, SeAcaboElTiempoDeEspera)
        signal.alarm(TiempoDeEspera)  #180 segundos
        #....................................................................
        print('\r'+Texto, end=' ')
        #print('\r'*term_width+''.join(copy), end=' '*(term_width-len(copy)))
        Texto = str()
        try:
            DefaultConfig = termios.tcgetattr(sys.stdin)
        except:
            DefaultConfig = None
        try:
            tty.setcbreak(sys.stdin.fileno())
            while(True):
                keycode = 0
                while True:
                    if select.select([sys.stdin, ], [], [], 0.0)[0]:
                        keycode = (keycode << 8) | ord(os.read(sys.stdin.fileno(), 1))
                    elif keycode != 0:
                        break
                if keycode == 127:    # BackSpace, Borrar
                    Texto = str()
                    continue
                if keycode == 27:     # ESC, Salir
                    Texto = 27
                    break
                if keycode == 10:     # ESC, Salir
                    Texto = chr(10)
                    break
                if keycode < 255 and len(Opciones) > 0 and chr(keycode).lower() in Opciones:
                    Texto = chr(keycode).lower()
                    break
        except TimeoutError:
            print('\nDetectado: TimeoutError')
            Texto = None
        except KeyboardInterrupt:
            print('\nDetectado: KeyboardInterrupt')
            Texto = None
        except:
            print('\nDetectado Excepcion: ', str(sys.exc_info()[0]))
            Texto = None
        finally:
            if DefaultConfig is not None:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, DefaultConfig)
        signal.alarm(0)          # Es importante Deshabilitar la Alarma
        print('\r\r')
        return(Texto)


#==============================================================================
#CLASE para Buscar, Escoger y Verificar Archivos en Directorios
#------------------------------------------------------------------------------
class MenuMagico(FuncionComun):

    def __init__(self):
        self.TipoArchivo = list()
        #self.TipoArchivo = ['pdf', 'txt', 'html', 'htm']
        self.Directorios = list()
        self.ArchivosEscogidos = list()
        self.Archivos = list()
        self.Opciones = list()
        self.Confirmacion = str()

    def scantree(self, RutaArchivo, Recursivo=False):
        for entrada in os.scandir(RutaArchivo):
            if entrada.is_dir(follow_symlinks=False) and Recursivo is True:
                yield from self.scantree(entrada.path) 
            else:
                yield entrada
    
    def BuscarArchivos(self, TipoArchivo=None, path='./', BuscarTodos=False, Recursivo=False):
        self.Directorios = list()
        self.Archivos = list()
        self.TipoArchivo = self.CrearLista(TipoArchivo)
        #------------------------------------------------------------------------
        #------------------------------------------------------------------------
        print('TipoArchivo: ', TipoArchivo, 'path: ', path, 'BuscarTodos: ', BuscarTodos, 'Recursivo: ', Recursivo)
        #------------------------------------------------------------------------
        #Buscar Archivos segun la Extension dada en 'TipoArchivo' o Todos si es None
        #for entrada in os.scandir(path):   #'entrada' es una Clase <DirEntry>
        for entrada in self.scantree(path, Recursivo=Recursivo):   #'entrada' es una Clase <DirEntry>
            if entrada.is_file():
                if BuscarTodos == True and (TipoArchivo == None or len(TipoArchivo) == 0):
                    self.Archivos.append(entrada)
                elif entrada.name.endswith(tuple(self.TipoArchivo)):
                    self.Archivos.append(entrada)
            elif entrada.is_dir():
                self.Directorios.append(entrada)
        self.TipoArchivo.sort()
        return(self.Archivos)


    def BorrarDeArchivosEncontrados(self, NombresCorrectos):
        self.Archivos = [a for a in self.Archivos if a not in NombresCorrectos]
        return(self)
        
    def EscogerArchivos(self):
        if self.Archivos:
            print(('\n\n{}'.format('-' * 80)))
            print((" Se encontro los siguientes archivos:"))
            for n, archivo in enumerate(self.Archivos):
                print(("   {:3}  {}".format(n + 1, archivo.path)))
            print(("   [ {} ]  {}".format(0, "Para Salir Escoja 0")))
            try:
                self.Opciones = self.inputs(" Ingrese los archivos para procesar [ENTER para todos]: ", 120)
                if type(self.Opciones) is str:
                    self.Opciones = self.Opciones.replace(',', ' ').split()
                    self.Opciones = [int(x) for x in self.Opciones if x.isdigit() and int(x) < (1 + len(self.Archivos))]
                    if len(self.Opciones) == 0:
                        self.Opciones = list(range(1, 1 + len(self.Archivos)))
                    if self.Opciones.count(0) > 0:
                        if self.Opciones.index(0) > 0:
                            self.Opciones = [self.Opciones[x] for x in range(self.Opciones.index(0))]
                        else:
                            raise
                    self.ArchivosEscogidos = [self.Archivos[x - 1] for x in self.Opciones]
                    print(('\n Opciones Ingresadas  : {}'.format(self.Opciones)))
                    #print(('Archivos Escogidos : {}'.format(self.ArchivosEscogidos)))
                    print(('{}'.format('-' * 80)))
                    return 1
            except:
                pass
            self.ArchivosEscogidos = list()
            self.Archivos = list()
            self.Opciones = list()
        return 0

    #Para verificar que existen los archivos ingresados o encontrados
    def ExistenArchivos(self):
        if len(self.ArchivosEscogidos) > 0:
            for Archivo in reversed(self.ArchivosEscogidos):
                if os.path.isfile(Archivo.path):
                    pass
                    print(('   Existe el Archivo    : {}'.format(Archivo)))
                else:
                    print(('   No Existe el Archivo : {}  (se ha removido)'.format(Archivo)))
                    self.ArchivosEscogidos.remove(Archivo)
            if len(self.ArchivosEscogidos) > 0:
                #self.iNombreArchivo = iter(self.ListaDeArchivos)
                return(True)
        return(False)

    #------------------------------------------------------------------------------
    def Renombrar(self, NombreArchivo, NuevoNombre):
        if os.path.isfile(NombreArchivo):
            if os.path.isfile(NuevoNombre):
                #Cuando el Archivo Existe, Agregar '.' al nombre
                NuevoNombre, Extension = self.ObtenerNombreyExtension(NuevoNombre)
                NuevoNombre += '.'
                while os.path.isfile(NuevoNombre + Extension):
                    #Si el mismo archivo se encuentra entonces salir
                    if '{}.{}'.format(NuevoNombre, Extension) == NombreArchivo:
                        print('    Nombre es OK: {}'.format(NombreArchivo))
                        return(True)
                    print(' Existe el Archivo: {}'.format(NombreArchivo))
                    NuevoNombre += '.'
                NuevoNombre += Extension
            os.rename (NombreArchivo, NuevoNombre)
            print('    Renombrado a: {}'.format(NuevoNombre))
            return(True)
        else:
            print(' No Existe el Archivo : {}'.format(NombreArchivo))
        return(False)

    #------------------------------------------------------------------------------
    #Solicita confirmacion (S) 'Si', (N) 'No', (T) 'Todos Si', en mayuscula o minuscula
    def SeleccionarProcedimiento(self, MsgAviso=' Desea proceder? ([S]i, [N]o, [T]odo Si) (ESC: Salir) (ENTER: No) : ', TimeOver=180, NuevaOpcion=None):
        #' Desea proceder? [(S)Si, (N)No, (T)Todo Si] (ESC->Salir) (ENTER->No) : '
        if self.Confirmacion == 't':
            return(True)
        try:
            while (True):
                #Devuelve: ESC = 27, ENTER = 10, TimeOver = None
                Opcion = self.GetOptionKeys(Texto=MsgAviso, Opciones=['s', 'n', 't'], TiempoDeEspera=TimeOver, NumChar=1)
                self.Confirmacion = Opcion
                if Opcion == 27:
                    return(Opcion)
                if Opcion == '\n' or Opcion is None or Opcion == 'n' or Opcion == 'no':
                    return(False)
                if Opcion == 's' or Opcion == 'si' or Opcion == 't':
                    return(True)
                if NuevaOpcion is not None:
                    if type(NuevaOpcion) is tuple:
                        NuevaOpcion = list(NuevaOpcion)
                    if type(NuevaOpcion) is not list:
                        NuevaOpcion = [NuevaOpcion, ]
                    for item in NuevaOpcion:
                        if str(item).lower() == Opcion:
                            return(item)
        except:
            self.Confirmacion = str()
            print('\r\r')
        return(None)

#==============================================================================
#CLASE para Normalizar Palabras y Fragmentos de Texto
#------------------------------------------------------------------------------
class Normalize(object):
    SeparadoresPalabra = (' ', '_', '+', ',', '.', '-')
    SiempreMinuscula = ( 'y', 'el', 'la', 'lo', 'al', 'de', 'es', 'en', 'mi', 'tu', 'que',
                         'del', 'las', 'los', 'con', 'por', 'has', 'como', 'www', 'para',
                         'desde', 'un',
                         'and', 'the', 'this', 'of', 'to', 'is', 'in', 'my', 'me', 'what',
                         'with', 'for', 'have', 'has', 'since', 'from', 'as', 'or', 'et' )
    SiempreMayuscula = ('pdf', 'dms', 'csd', 'ucv', 'cv', 'acdc', 'usa', 'bcp', 'eecc', 'aac',
                        'usa', 'ac3', 'iigm', 'db', 'gprs', 'gsm', 'cd', 'hd', 'tv', 'ibm',
                        'html', 'htm', 'vhf', 'gps',
                        'bbc', 'abc', 'dvd', 'ii', 'iii', 'iv', 'o', 'vi', 'vii', 'viii',
                        'ix', 'x', 'xi', 'xii', 'xiii', 'xiv', 'xv', 'xvi', 'xvii', 'xviii',
                        'xix', 'xx')
    SiempreAsi = ('HDRip', 'DVDRip')
    PermitirPrimerCaracter = ('#', '$', '&', '(', ')', '¿', '?', '¡', '!', '[', ']', '{', '}', '_', '-',
                            ',', '.', ':', ';', '<', '>')
    SiempreCapital = ('yo', 'dr', 'sr', 'mr', 'ud')
    SimbAgrupacion = (('(', ')'), ('[', ']'), ('{', '}'), ('<', '>'))
    SimbAgrupacion = (('(', ')'), ('[', ']'), ('{', '}'), ('<', '>'), ('¿', '?'), ('¡', '!'))

    def __init__(self, TextoIngresado=str()):
        self.Fragmento = TextoIngresado
        self.NumeroDeCopia = str()

    def Automatico(self):
        self.ReplaceHTML()
        self.ReconocerNumeroDeCopia()
        self.ReemplazarSeparadorPorEspacio()
        self.VerificarEspacios()
        self.TraducirSignos()
        self.SimbolosDobles()
        self.Titularizar()
        self.ReconocerNumeroDeCopia(Reponer=True)
        self.VerificarEspacios()
        self.Punto()
        return(self)

    def ReconocerFecha():
        pass

    #----------------------------------------------------------------------------------------------
    def ReconocerNumeroDeCopia(self, Reponer=False):
        if Reponer == False:
            self.NumeroDeCopia = str()
            NumCopia = re.search('\([0-9]\)$', self.Fragmento)
            if NumCopia and NumCopia.span()[1] == len(self.Fragmento):
                self.NumeroDeCopia = NumCopia.group()
                self.Fragmento = self.Fragmento[:NumCopia.span()[0]].strip()
                return(True)
        elif len(self.NumeroDeCopia) > 1:
            self.Fragmento = '{} {}'.format(self.Fragmento, self.NumeroDeCopia)
        self.NumeroDeCopia = str()
        return(False)
        
    #----------------------------------------------------------------------------------------------
    #Reemplaza 'SeparadoresPalabra' por espacios
    def ReemplazarSeparadorPorEspacio(self):
        Separador = str()
        Contador = 0
        if self.Fragmento.count(' ') == 0:
            for item in self.SeparadoresPalabra:
                #Buscar el Separador con Mayor indicencia........
                if self.Fragmento.count(item) > Contador:
                    Contador = self.Fragmento.count(item)
                    Separador = item
                #................................................
            if Contador > 0 and len(Separador) > 0:
                self.Fragmento = self.Fragmento.replace(Separador, ' ').strip()
        return(self)

    #----------------------------------------------------------------------------------------------
    #Reconocer Caracteres Web y Reemplazarlos.
    #Traduce caracteres extraños: NFKD (Descompuesto) -> NFKC (Compuesto)
    #Tilde Operator  u'\u223C' '∼'  , u'\u007E' '~'
    #Small Tilde = u'\u02DC', Combining Tilde = u'\u0303', Swung Dash = u'\u2053'
    #Fullwidth Tilde = u'\uFF5E'
    def TraducirSignos(self):
        #----------------------------------------------------------------------
        #Metodo de Compara CATEGORIA 'Mn'. Quita Todo tambien la Virgulilla o tilde Ñ ñ
        #self.Fragmento = ''.join((c for c in normalize('NFD', self.Fragmento) if category(c) != 'Mn'))
        #----------------------------------------------------------------------
        #Metodo para Especificar el Caracter Extraño a Quitar, no elimina '~' = ('\u0303') para ñ, Ñ
        BorrarSignos = dict.fromkeys([ch for ch in range(ord('\u0300'), ord('\u036f')) if ch != ord('\u0303')])
        #Falla si '~' es ã o esta sobre una e, i, o, u
        self.Fragmento = normalize('NFD', self.Fragmento)    #Descomposicion
        self.Fragmento = self.Fragmento.translate(BorrarSignos)
        self.Fragmento = normalize('NFC', self.Fragmento)    #Composicion
        #----------------------------------------------------------------------
        #Metodo con 'import re', no elimina la ñ, Ñ
        #self.Fragmento = normalize( "NFD", self.Fragmento)   #Descomposicion
        #self.Fragmento = re.sub(r"([^n\u0300-\u036f]|n(?!\u0303(?![\u0300-\u036f])))[\u0300-\u036f]+", r"\1", self.Fragmento, 0, re.I)
        #self.Fragmento = normalize( 'NFC', self.Fragmento)   #Composicion
        #----------------------------------------------------------------------
        return(self)

    #----------------------------------------------------------------------------------------------
    #Simbolos Dobles de Agrupacion
    #Paréntesis () Texto aclaratorio, Opcion, Dato, fecha, lugar o significado de siglas
    #Corchetes  [] Transcripciones Foneticas, Marcar Modificacion, Aclaraciones, Enmiendas
    #Llaves     {} Esquemas, Cuadros Sinopticos para establecer clasificaciones y agrupar opciones diferentes
    #En Fragmentos se usan de la siguiente forma: (…[…{…}…]…).
    def SimbolosDobles(self):
        for c1, c2 in self.SimbAgrupacion:
            Cadena = self.Fragmento
            YaProcesado = str()
            while True:
                x1, x2 = (Cadena.find(c1), Cadena.find(c2))
                if ((x1 < 0) and (x2 < 0)):     #Fin del Proceso
                    self.Fragmento = YaProcesado + Cadena
                    self.Fragmento = self.Fragmento.replace(c1, ' {} '.format(c1))
                    self.Fragmento = self.Fragmento.replace(c2, ' {} '.format(c2))
                    self.VerificarEspacios()
                    self.Fragmento = self.Fragmento.replace('{} '.format(c1), c1)
                    self.Fragmento = self.Fragmento.replace(' {}'.format(c2), c2)
                    break
                elif ((x1 >= 0) and (x2 < 0)):  #No hay caracter c2, ')' o ']' o '}'
                    #Ejemplo: Cadena = 'Revista (1986 - (Historia Antigua (Castellano'
                    #Entonces borrar todos c1 y continuar. IDEA: Agregar c2 una palabra despues en ' ')
                    Cadena = Cadena.replace(c1, ' ')
                elif ((x1 < 0) and (x2 >=0)):   #No hay caracter c1, '(' o '[' o '{'
                    #Ejemplo: Cadena = 'Revista 1986) - Historia) Antigua Castellano)'
                    #Entonces borrar todos c2 y continuar. IDEA: Agregar c1 una palabra antes en ' ')
                    Cadena = Cadena.replace(c2, ' ')
                elif (x1 > x2):
                    #Ejemplo: Cadena = 'Revista 1986) - Historia) Antigua (Castellano)'
                    #Segmento <x2, x1> es ') - Historia) Antigua ('
                    #Entonces borrar todo c2 y continuar. En el Futuro Agregar c1 '(' una palabra antes)
                    Cadena = Cadena[:x2] + Cadena[x2, x1].replace(c2, ' ') + Cadena[x1:]
                    #print(('x1 > x2 : {}, {} y Cadenas: |{}|{}|{}|'.format(x1, x2, Cadena[:x2], Cadena[x2, x1], Cadena[x1:], )))
                elif (x1 < x2):
                    #Caso Normal: Cadena = 'Revista (1986) - Historia) Antigua (Castellano)'
                    #Segmento <x1, x2> es '(1986)'
                    #Entonces Cadena = ' - Historia) Antigua (Castellano)' y continuar
                    YaProcesado += Cadena[:x2 + 1]
                    Cadena =  Cadena[x2 + 1:]
                    #print(('x1 < x2 : {}, {} y Cadenas: |{}|   |{}|'.format(x1, x2, YaProcesado, Cadena)))
        return(self)

    #----------------------------------------------------------------------------------------------
    def ReplaceHTML(self):
        TablaHTML = { "&ntilde;" : 'n', "&Ntilde;" : 'N',
                      "&aacute;" : 'a', "&eacute;" : 'e', "&iacute;" : 'i', "&oacute;" : 'o', "&uacute;" : 'u',
                      "&Aacute;" : 'A', "&Eacute;" : 'E', "&Iacute;" : 'I', "&Oacute;" : 'O', "&Uacute;" : 'U',
                      "&euro;"   : '€', "&lt;"     : '<', "&gt;"     : '>', "&amp;"    : '&', "&nbsp;"   : ' ',
                      "%2B"      : '+', "%20"      : ' ', "&quot;"   : None,"&apos;"   : None, "Ã±"      : 'n',
                      "Ã³"       : 'o',
                    }
        for Code in TablaHTML.keys():
            if self.Fragmento.find(Code) >= 0:
                self.Fragmento = self.Fragmento.replace(Code, ' ' if TablaHTML[Code] is None else TablaHTML[Code])
        for c in self.Fragmento:
            if ord(c) >= 0xFFF0:
                self.Fragmento = self.Fragmento.replace(c, '&')
        return(self)

    #----------------------------------------------------------------------------------------------
    # Utiliza: self.AnalizarPalabra()
    def Titularizar(self):
        Original = self.Fragmento
        #----------------------------------------------------------------------
        Nuevo = list()
        for self.Fragmento in Original.split():
            if self.Fragmento:
                Nuevo.append(self.AnalizarPalabra().Str() if Nuevo else self.AnalizarPalabra().Str().capitalize())
        Nuevo = ' '.join(Nuevo).strip()
        self.Fragmento = Nuevo if Nuevo else Original
        #----------------------------------------------------------------------
        #CODIGO PROVISIONAL
        #Despues de un '-' debemos de Capitalizar. Falla los SiempreMayuscula
        Segmentos = self.Fragmento.split('-')
        for n, item in enumerate(Segmentos):
            palabras = item.split()
            if len(palabras) > 1 and palabras[0].lower() not in self.SiempreMayuscula:
                SoloLetraNum = ''.join(s if s.isalnum() else ' ' for s in palabras[0]).split()
                if SoloLetraNum:
                    SoloLetraNum = SoloLetraNum[0]
                    if SoloLetraNum in self.SiempreMinuscula:
                        if len(palabras[1]) > 0:
                            # falla en '- de un -' cambia a: '- De un -'
                            Segmentos[n] = Segmentos[n].replace(SoloLetraNum, SoloLetraNum.capitalize(), 1)
                            self.Fragmento = '-'.join(Segmentos)
                    else:
                        Segmentos[n] = Segmentos[n].replace(SoloLetraNum, SoloLetraNum.capitalize(), 1)
                        self.Fragmento = '-'.join(Segmentos)
        return(self)

    #----------------------------------------------------------------------------------------------
    #Una Palabra de Texto se modificara segun las siguientes reglas:
    #     1. Si la Palabra esta en 'SiempreMinuscula' poner a minuscula
    #     2. Si la Palabra esta en 'SiempreMayuscula' poner a mayuscula
    #     3. Si la palabra esta en 'SiempreAsi' poner segun se indica
    #     4. Si no ocurre nada se llama a 'Capitalizar'
    def AnalizarPalabra(self):
        #Aqui no se puede 'capitalizar', por que afecta a todas las palabras una a una
        palabra = self.Fragmento.lower()
        if palabra:
            SoloLetraNum = ''.join(s if s.isalnum() else ' ' for s in palabra).split()
            if SoloLetraNum:
                SoloLetraNum = SoloLetraNum[0]
                if SoloLetraNum in self.SiempreMinuscula:
                    #Falla en Textos: (¡es¡todo_moda)
                    self.Fragmento = palabra
                elif SoloLetraNum in self.SiempreMayuscula:
                    self.Fragmento = palabra.upper()
                else:
                    try:
                        if palabra.find(SoloLetraNum) >= 0:
                            #print('SoloLetraNum: {}, palabra: {}'.format(SoloLetraNum, palabra))
                            indice = [s.lower() for s in self.SiempreAsi].index(SoloLetraNum)
                            self.Fragmento = palabra.replace(SoloLetraNum, self.SiempreAsi[indice], 1)
                        else:
                            raise
                    except:
                        self.Capitalizar()
        return(self)

    #----------------------------------------------------------------------------------------------
    #Capitalizar segun las siguientes reglas:
    #     1. Si la primera Letra es del Alfabeto [a..z]
    #     3. Si la palabra esta en 'SiempreCapital', MEJORAR ESTO, PORQUE NO HACE NADA
    #     2. Si primer caracter esta en 'PermitirPrimeraLetra' buscar el siguiente caracter
    #     2. Si primer caracter es un numero [0..9] buscar el siguiente caracter
    # Si no se encuentra ninguna de esta reglas SALIR y el Texto queda igual
    def Capitalizar(self):
        expresion = self.Fragmento.lower()
        if expresion:
            if expresion[0].isalpha() or expresion in self.SiempreCapital:
                if expresion not in self.SiempreCapital and len(expresion) == 1:
                    #Para Expresiones como: 'A', 'b', 'w' no hacer nada
                    pass
                elif len(expresion) == 2 and len(expresion) == sum(expresion.lower().count(w) for w in 'bcdfghjklmnpqrstvwxyz'):
                    #Para expresiones tipo 'BB', 'ab', 'qw', 'jG' no hacer nada
                    pass
                else:
                    self.Fragmento = expresion.capitalize()
            else:
                #Primer Caracter no es letra del Alfabeto, Puede ser Numero o Caracter Extraño
                for n in expresion:
                    if n in self.PermitirPrimerCaracter or n.isdigit():
                        continue
                    else:
                        if n.isalpha():
                            #Falta incluir SiempreMinuscula, SiempreMayuscula
                            #Se encontro un Caracter Alfabetico
                            #Verificar que la longitud sea mayor a 2, sino salir
                            resto = ''.join(s for s in expresion if s.isalpha())
                            if len(resto) < 3:
                                break
                            self.Fragmento = expresion.replace(n,n.upper(),1)
                        break
        return(self)

    #Elimina varios espacio seguidos y deja solo uno. Elimina el espacio en los extremos
    def VerificarEspacios(self):
        self.Fragmento = self.Fragmento.replace(',', ', ')
        
        #.......................................................
        #Falla en archivos como: 'OSINERG No.236-2005-OS-CD-Norma'  => 'Osinerg No.236 - 2005 - Os - CD - Norma'
        #No se puede dar espacio en forma bruta, primero hay analizar
        self.Fragmento = self.Fragmento.replace('-', ' - ')
        #.......................................................
        
        #Agregar Espacio en (), [], {}, ejemplo '(uno)es' en '(uno) es', pero si hay otro (), [], {} NO: ejemplo: '(uno)(dos)'
        #self.Fragmento = self.Fragmento.replace(')', ') ')
        #self.Fragmento = self.Fragmento.replace(')', ') ')
        self.Fragmento = ' '.join(self.Fragmento.split())
        return(self)

    #Elimina varios puntos seguidos y deja solo uno. Elimina el Espacio de la derecha
    def Punto(self):
        if self.Fragmento.count('.') > 0:
            self.Fragmento = '.'.join(x.rstrip() for x in self.Fragmento.split('.') if len(x) > 0)
            if self.Fragmento.count('.') > 1:
                self.Fragmento = '.'.join(x.rstrip() for x in self.Fragmento.split('.') if len(x) > 0)
        return(self)

    def Str(self):
        return(self.Fragmento)

    def __str__(self):
        return(self.Fragmento)


#==============================================================================
#CLASE para Reparar los nombres de Archivos en Directorios
#------------------------------------------------------------------------------
FILESNAME = 1

class RepararNombreDeArchivos(FuncionComun):

    OtrosSeparadoresDePalabra = ('_', '+', '.', '-', ',')

    class RegistroDelNombre():

        def __init__(self, ):
            self.NombreArchivo = str()
            self.Ruta = str()
            self.NombreAntes = str()
            self.NombreNuevo = str()
            self.Extension = str()

    def __init__(self, TextoIngresado=str(), Modo=FILESNAME):
        self.Reg = self.RegistroDelNombre()
        if Modo == FILESNAME and len(TextoIngresado) > 0:
            self.Reg.NombreArchivo = TextoIngresado
            self.Reg.Ruta = os.path.dirname(TextoIngresado)
            self.Reg.NombreAntes, self.Reg.Extension = self.ObtenerNombreyExtension(os.path.basename(TextoIngresado))
            self.Reg.NombreNuevo = self.Reg.NombreAntes

    # Arreglar la Sintaxis, Existen dos modos:
    #     1. FILESNAME, usado para nombres de archivos
    #     2. TEXTLINE, usado para fragmentos de texto
    def CorregirSintaxis(self, Modo=FILESNAME):
        #Palabras como SF2 -> (Title) Sf2 (Mal) -> (Arreglar) SF2
        #Palabras como SFPack -> (Title) Sfpack (Mal) -> (Arreglar) SFPack
        #Palabras como 'M-Theory' se convierte en 'M-theory' y esta mal, debe ser igual 'M-Theory'
        return(self)

    # Arregla la Numeracion del Fragmento: "1. Nombre" o "01. Nombre" #def Numeracion(self):
    def RectificarNumeracion(self, Modo=FILESNAME):
        return(self)

    # El Texto agrupado con (), []. {} los mueve al final del texto
    #Simbolos Dobles de Agrupacion
    #Paréntesis () Texto aclaratorio, Opcion, Dato, fecha, lugar o significado de siglas
    #Corchetes  [] Transcripciones Foneticas, Marcar Modificacion, Aclaraciones, Enmiendas
    #Llaves     {} Esquemas, Cuadros Sinopticos para establecer clasificaciones y agrupar opciones diferentes
    #En Fragmentos se usan de la siguiente forma: (…[…{…}…]…).

    SimbAgrupacion = (('(', ')'), ('[', ']'), ('{', '}'))

    def MoverSignosDeAgrupacion(self, Modo=FILESNAME):
        Numeracion = str()
        Cadena = self.Reg.NombreNuevo
        Simbolos = ''.join(''.join(sim for sim in grupo) for grupo in self.SimbAgrupacion)
        for n in (0, 1, 2):
            #Detectar Numeracion o Caracter Permitido...........
            #Ej: '1. (Ebook) Nombre del Libro'
            for pos, caracter in enumerate(Cadena):
                if caracter in Simbolos:
                    if pos > 0 and pos < 7 and (pos + 2) < len(Cadena):
                        item = Cadena[0:pos].strip()
                        if item.count(' ') == 0:
                            test = ''.join(c for c in item if c in '0123456789.-_()[]')
                            if test == item:
                                test = ''.join(c for c in item if c in '0123456789')
                                Numeracion = item.replace(test, '{:02}'.format(int(test)))
                                Cadena = Cadena[pos:]
                                break
            #...................................................
            for c1, c2 in self.SimbAgrupacion:
                tmp = str()
                while Cadena[0] == c1:
                    x2 = Cadena.find(c2)
                    if x2 > 0:
                        tmp += ' {}'.format(Cadena[:x2 + 1])
                        Cadena = Cadena[x2 + 1:].strip()
                        if Cadena[0] in ('(', '[', '{'):
                            continue
                        else:
                            while Cadena[0] in ('-', '_', '.', ',', ' '):
                                Cadena = Cadena[1:]
                        #if not Cadena[0].isalnum():
                Cadena += tmp
        self.Reg.NombreNuevo = '{} {}'.format(Numeracion.strip(), Cadena.strip())
        return(self)

    # Utiliza un diccionarios 'ESPAÑOL' para buscar y corregir palabras
    def CorrecionOrtografica(self ):
        return(self)

    # Crear una 'Lista de Autores' para corregir nombres de los autores: {apellido}, {nombre}
    # Y escoger entre dos formato para renombrar el libro:
    #       Formato 1:  {autor} - {nombre del libro} - {año} - etc.extension
    #       Formato 2:  {nombre del libro} {año} - {autor} – etc.extension
    def AcomodarAutoresNombreDeLibros(self, FORMATO=2):
        return(self)

    def Automatico(self):
        #AQUI REPARAMOS EL NOMBRE DEL ARCHIVO
        #----------------------------------------------------------------------
        self.Reg.NombreNuevo = Normalize(self.Reg.NombreNuevo).Automatico().Str()
        #LUEGO (FALTA IMPLEMENTAR):
        #self.CorregirSintaxis().FiltrarAlfabeto()
        self.RectificarNumeracion()
        self.MoverSignosDeAgrupacion()
        self.CorrecionOrtografica()
        self.AcomodarAutoresNombreDeLibros(FORMATO=2)
        self.Reg.NombreNuevo = Normalize(self.Reg.NombreNuevo).Automatico().Str()
        #----------------------------------------------------------------------
        return(self)

    def Str(self):
        RutaNombre = '{}{}'.format(self.Reg.Ruta, self.Reg.NombreNuevo.strip())
        if len(self.Reg.Extension.strip()) > 0:
            RutaNombre += '{}{}'.format('.', self.Reg.Extension.strip())
        return(RutaNombre)

    def Nombre(self):
        return(self.Reg.NombreNuevo)
        
    def Extension(self):
        return(self.Reg.Extension)


def MostrarCarita(msg=str(), Veces=1, Parpadeo=3, Tiempos=[0.24, 0.1, 0.4]):
    OjosAbiertos = '{}{} ({{º_º}} Aaah hh h ...) '.format('\r'*3, msg)
    OjosCerrados = '{}{} ({{-_-}} ZZZz zz z ...) '.format('\r'*3, msg)
    OjosSorpresa = '{}{} ({{0_0}} AAhh zz z ...) '.format('\r'*3, msg)
    for k in range(Veces):
        for Ojos, n in zip([OjosAbiertos, OjosCerrados]*Parpadeo, Tiempos[0:2]*Parpadeo):
            print(Ojos, end=' ')
            sleep(n)
        print(OjosAbiertos, end=' ')
        sleep(Tiempos[1])
        print(OjosSorpresa, end=' ')
        sleep(Tiempos[2])
    print(OjosCerrados, end=' ')


#==============================================================================
#La variable __name__ sirve para distinguir si el archivo se utiliza como un script
#o como un módulo importable
#Si se ejecuta como script, __name__ sera "main" y se procesará el siguiente codigo
#Si este Modulo es importado con "import" este codigo será ignorado
#------------------------------------------------------------------------------
if __name__ == "__main__":
    #==========================================================================
    #PARAMETROS Ingresados en la linea de comandos
    #--------------------------------------------------------------------------
    Descripcion = '''{0} V2.1 - 2019.08.29 (c) 2019
Programa para arreglar el nombre de los archivos, quitar caracteres extraños, colocar
cada palabra con letra inicial en mayuscula, reparar sintaxis, etc
    '''
    Descripcion = Descripcion.format(os.path.basename(__file__).upper())
    EjemploMsg = '''  Ejemplo:
            {0} txt pdf odt
            {0} -r -d /home/user odt doc pdf
            {0} -r txt pdf odt
            '''
    EjemploMsg = EjemploMsg.format(os.path.basename(__file__))
    #..........................................................................
    #Implementamos los Parametros
    MisParametros = argparse.ArgumentParser(description=Descripcion,
                                            epilog=EjemploMsg,
                                            formatter_class=argparse.RawDescriptionHelpFormatter)
    MisParametros.add_argument("-r", "--recursivo", action='store_true', help="Indica que buscara en forma recursiva en todos los directorios, si no se especifica convertira solo los archivos que encuentre en el directorio actual.")
    MisParametros.add_argument("-d", "--dir", default="./", help="Indica la ruta de trabajo, desde donde empezar la conversion, si no se especifica, usa el directorio actual.")
    #MisParametros.add_argument("-e", "--eliminar", default="._", help="Eliminar cada uno de los caracteres especificados en la cadena de texto.")
    #MisParametros.add_argument("-s", "--eliminar", default="._", help="Sustituir cada uno de los caracteres especificados en la cadena de texto por un caracter de espacio.")
    MisParametros.add_argument ("Tipos", nargs='*', help = "Es la lista de extensiones que debe de buscar, deben estar separados por espacios. Si no se especifica busca todos")
    args = MisParametros.parse_args()
    #..........................................................................
    #Parametros ingresados
    #TiposExt = args.Tipos
    #==========================================================================
    #PROGRAMA PRINCIPAL
    #--------------------------------------------------------------------------
    #Reparar = RepararNombreDeArchivos()
    Menu = MenuMagico()
    #Buscar Archivos Ingresados. Si no hay Extensiones ingresadas buscar todos los archivos
    NombresCorrectos = list()
    for Archivo in Menu.BuscarArchivos(TipoArchivo=args.Tipos, path=args.dir, BuscarTodos=True, Recursivo=args.recursivo):
        NuevoNombre = RepararNombreDeArchivos(Archivo.name).Automatico().Str()
        NuevoNombre = RepararNombreDeArchivos(NuevoNombre).MoverSignosDeAgrupacion().Str()
        if Archivo.name.strip() == NuevoNombre.strip():
            NombresCorrectos.append(Archivo)
    Menu.BorrarDeArchivosEncontrados(NombresCorrectos)
    #Escoger los archivos para procesar
    if Menu.EscogerArchivos():
        Total = len(Menu.ArchivosEscogidos)
        for Num, Archivo in enumerate(Menu.ArchivosEscogidos):
            NuevoNombre = RepararNombreDeArchivos(Archivo.name).Automatico().Str()
            NuevoNombre = RepararNombreDeArchivos(NuevoNombre).MoverSignosDeAgrupacion().Str()
            if Archivo.name.strip() != NuevoNombre.strip():
                print('{:2} de {:2} Renombrar:\n Nombre Original  :  {}'.format(Num + 1, Total, Archivo.path))
                FullNuevoNombre = '{}/{}'.format(os.path.dirname(Archivo.path), NuevoNombre)
                print(  ' Nuevo Nombre     :  {}'.format(FullNuevoNombre))
                Opcion = Menu.SeleccionarProcedimiento()
                print('\r\r')
                if Opcion == 27:
                    break
                if Opcion == True:
                    Menu.Renombrar(Archivo.path, FullNuevoNombre)
                    print('\r\r')
        MostrarCarita('Terminado. ')
        print('\r\r\n')
    else:
        print("\nMuy bien... no hay Archivos {} para procesar".format(Menu.TipoArchivo))

    #--------------------------------------------------------------------------
    # Para mostrar la AYUDA
    #print(MisParametros.parse_args(['-h']))

        
