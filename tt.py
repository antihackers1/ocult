#!/usr/bin/env python3
"""
Proxy Checker - Verifica proxies desde un archivo de texto
"""

import requests
import concurrent.futures
import time
from typing import List, Tuple
import argparse
import sys

# Configuración
TIMEOUT = 10  # Timeout en segundos para cada proxy
TEST_URL = "http://www.google.com"  # URL para probar los proxies
MAX_WORKERS = 50  # Número de threads concurrentes


class ProxyChecker:
    def __init__(self, proxy_file: str, output_file: str = None, timeout: int = TIMEOUT):
        self.proxy_file = proxy_file
        self.output_file = output_file or "working_proxies.txt"
        self.timeout = timeout
        self.working_proxies = []
        self.failed_proxies = []
        self.total_proxies = 0
        
    def load_proxies(self) -> List[str]:
        """Carga los proxies desde el archivo de texto"""
        try:
            with open(self.proxy_file, 'r', encoding='utf-8') as f:
                proxies = [line.strip() for line in f if line.strip()]
            self.total_proxies = len(proxies)
            print(f"[+] Cargados {self.total_proxies} proxies desde {self.proxy_file}")
            return proxies
        except FileNotFoundError:
            print(f"[!] Error: No se encontró el archivo {self.proxy_file}")
            sys.exit(1)
        except Exception as e:
            print(f"[!] Error al leer el archivo: {e}")
            sys.exit(1)
    
    def check_proxy(self, proxy: str) -> Tuple[str, bool, float]:
        """
        Verifica si un proxy funciona
        Retorna: (proxy, funciona, tiempo_respuesta)
        """
        # Formato esperado: ip:puerto o protocolo://ip:puerto
        if '://' not in proxy:
            proxy_url = f"http://{proxy}"
        else:
            proxy_url = proxy
        
        proxies = {
            'http': proxy_url,
            'https': proxy_url
        }
        
        start_time = time.time()
        try:
            response = requests.get(
                TEST_URL,
                proxies=proxies,
                timeout=self.timeout,
                allow_redirects=True
            )
            elapsed = time.time() - start_time
            
            if response.status_code == 200:
                return (proxy, True, elapsed)
            else:
                return (proxy, False, elapsed)
                
        except requests.exceptions.ProxyError:
            return (proxy, False, 0)
        except requests.exceptions.ConnectTimeout:
            return (proxy, False, 0)
        except requests.exceptions.ReadTimeout:
            return (proxy, False, 0)
        except requests.exceptions.ConnectionError:
            return (proxy, False, 0)
        except Exception as e:
            return (proxy, False, 0)
    
    def check_all_proxies(self, proxies: List[str]):
        """Verifica todos los proxies usando multithreading"""
        print(f"\n[*] Iniciando verificación con {MAX_WORKERS} workers...")
        print(f"[*] URL de prueba: {TEST_URL}")
        print(f"[*] Timeout: {self.timeout}s\n")
        
        checked = 0
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            future_to_proxy = {executor.submit(self.check_proxy, proxy): proxy for proxy in proxies}
            
            for future in concurrent.futures.as_completed(future_to_proxy):
                proxy, is_working, response_time = future.result()
                checked += 1
                
                if is_working:
                    self.working_proxies.append(proxy)
                    print(f"[✓] {proxy} - Funciona ({response_time:.2f}s) [{checked}/{self.total_proxies}]")
                else:
                    self.failed_proxies.append(proxy)
                    print(f"[✗] {proxy} - No funciona [{checked}/{self.total_proxies}]")
        
        elapsed_total = time.time() - start_time
        
        print(f"\n{'='*60}")
        print(f"[+] Verificación completada en {elapsed_total:.2f}s")
        print(f"[+] Proxies funcionando: {len(self.working_proxies)}/{self.total_proxies}")
        print(f"[+] Proxies fallidos: {len(self.failed_proxies)}/{self.total_proxies}")
        print(f"[+] Tasa de éxito: {(len(self.working_proxies)/self.total_proxies*100):.2f}%")
        print(f"{'='*60}\n")
    
    def save_working_proxies(self):
        """Guarda los proxies que funcionan en un archivo"""
        if not self.working_proxies:
            print("[!] No hay proxies funcionando para guardar")
            return
        
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                for proxy in self.working_proxies:
                    f.write(f"{proxy}\n")
            print(f"[+] Proxies funcionando guardados en: {self.output_file}")
        except Exception as e:
            print(f"[!] Error al guardar los proxies: {e}")
    
    def run(self):
        """Ejecuta el proceso completo de verificación"""
        print("\n" + "="*60)
        print(" "*15 + "PROXY CHECKER")
        print("="*60)
        
        proxies = self.load_proxies()
        if not proxies:
            print("[!] No se encontraron proxies en el archivo")
            return
        
        self.check_all_proxies(proxies)
        self.save_working_proxies()


def main():
    # Declarar variables globales al inicio
    global MAX_WORKERS, TEST_URL
    
    parser = argparse.ArgumentParser(
        description='Proxy Checker - Verifica proxies desde un archivo de texto',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python3 proxy_checker.py proxies.txt
  python3 proxy_checker.py proxies.txt -o working.txt
  python3 proxy_checker.py proxies.txt -t 5 -w 100
        """
    )
    
    parser.add_argument('input_file', help='Archivo de texto con los proxies (formato: ip:puerto)')
    parser.add_argument('-o', '--output', default='working_proxies.txt', 
                       help='Archivo de salida para proxies funcionando (default: working_proxies.txt)')
    parser.add_argument('-t', '--timeout', type=int, default=TIMEOUT,
                       help=f'Timeout en segundos para cada proxy (default: {TIMEOUT})')
    parser.add_argument('-w', '--workers', type=int, default=MAX_WORKERS,
                       help=f'Número de workers concurrentes (default: {MAX_WORKERS})')
    parser.add_argument('-u', '--url', default=TEST_URL,
                       help=f'URL para probar los proxies (default: {TEST_URL})')
    
    args = parser.parse_args()
    
    # Actualizar configuración global
    MAX_WORKERS = args.workers
    TEST_URL = args.url
    
    # Crear y ejecutar el checker
    checker = ProxyChecker(
        proxy_file=args.input_file,
        output_file=args.output,
        timeout=args.timeout
    )
    
    try:
        checker.run()
    except KeyboardInterrupt:
        print("\n\n[!] Proceso interrumpido por el usuario")
        sys.exit(0)


if __name__ == "__main__":
    main()
