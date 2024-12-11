# Búsqueda de valores de enlaces dentro de una URL ingresada

import urllib.request, urllib.parse, urllib.error
import re
import ssl

# Ignorar errores de certificado SSL
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

url = input('Introduzca - ')
html = urllib.request.urlopen(url).read()
nums = re.findall('[0-9]+', html)

print(nums)

#for enlace in enlaces:
#    print(enlace.decode())
 #   for linea in fh:
  #  linea = linea.rstrip()
   # if re.findall('[0-9]+', linea):
    #    for cad in re.findall('[0-9]+', linea):
     #       vals = int(cad)
      #      nums.append(vals)
            
#print(sum(nums))       