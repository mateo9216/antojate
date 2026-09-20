# Imagen de Antójate = ERPNext oficial + la app custom `antojate`.
#
# Partimos de la imagen ya construida de ERPNext (no de frappe/build) porque
# un `bench init` completo tarda ~20 min y descarga todo el toolchain de node.
# Aquí solo añadimos la app custom: la construcción tarda segundos.
#
# El código de la app NO queda congelado en la imagen: compose monta
# ../apps/antojate encima de esta ruta, así que editar en el host se refleja
# de inmediato en el contenedor. Lo que la imagen aporta es el `pip install -e`
# (registra la app en el entorno virtual del bench) y el enlace de assets.
ARG ERPNEXT_VERSION=v16.17.0
FROM frappe/erpnext:${ERPNEXT_VERSION}

USER frappe
WORKDIR /home/frappe/frappe-bench

COPY --chown=frappe:frappe apps/antojate /home/frappe/frappe-bench/apps/antojate

# 1) Registrar la app en el entorno del bench (editable: lee del bind mount).
# 2) Enlazar los assets estáticos dentro de /assets, que es el directorio que
#    el entrypoint de la imagen enlaza a sites/assets en cada arranque. Si el
#    enlace se creara en runtime, el siguiente arranque lo borraría.
RUN env/bin/pip install --no-cache-dir -e apps/antojate \
    && ln -sfn /home/frappe/frappe-bench/apps/antojate/antojate/public \
               /home/frappe/frappe-bench/assets/antojate
