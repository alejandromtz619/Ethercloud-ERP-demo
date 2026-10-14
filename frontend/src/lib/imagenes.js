const BACKEND_URL = (process.env.REACT_APP_BACKEND_URL || '').replace(/\/+$/, '');

/**
 * Resuelve la URL de una imagen guardada en el sistema.
 *
 * El backend guarda los ficheros subidos como rutas absolutas de su propio
 * dominio ("/uploads/productos/x.jpg"), pero el frontend se sirve desde otro
 * host, asi que una ruta relativa apuntaria al sitio equivocado y daria 404.
 * Las URLs externas (http/https) y los data: se devuelven sin tocar.
 */
export const resolverImagenUrl = (url) => {
  if (!url) return url;
  if (url.startsWith('/uploads/')) return `${BACKEND_URL}${url}`;
  return url;
};

export default resolverImagenUrl;
