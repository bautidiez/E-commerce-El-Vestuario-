import { Component, OnInit, ChangeDetectorRef, NgZone } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule, Router } from '@angular/router';
import { ApiService } from '../../../services/api.service';
import { AuthService } from '../../../services/auth.service';
import { ColorPickerComponent } from '../../../components/color-picker/color-picker.component';
import Swal from 'sweetalert2';

@Component({
  selector: 'app-productos-admin',
  imports: [CommonModule, FormsModule, RouterModule, ColorPickerComponent],
  templateUrl: './productos-admin.html',
  styleUrl: './productos-admin.css'
})
export class ProductosAdminComponent implements OnInit {
  productos: any[] = [];
  categorias: any[] = [];
  categoriasPadre: any[] = [];
  subcategoriasNivel1: any[] = [];  // Temporadas/Tipos (Retro, 24/25, etc.)
  subcategoriasNivel2: any[] = [];  // Ligas (Premier, La Liga, etc.)
  categoriaPadreSeleccionada: number | null = null;
  subcategoriaNivel1Seleccionada: number | null = null;
  mostrarSubcategorias = false;  // Solo mostrar subcategorías si es Remeras
  public colorSeleccionado: string = '';
  public productosRelacionados: any[] = [];
  public productoRelacionadoId: number | null = null;

  // Propiedades para la búsqueda de productos relacionados (Autocomplete)
  public busquedaProductoRelacionado: string = '';
  public productosRelacionadosFiltrados: any[] = [];
  public productosRelacionadosSeleccionados: any[] = []; // Lista de productos seleccionados

  // Selección múltiple
  productosSeleccionados: number[] = [];
  procesandoBulk = false;

  loading = true;
  mostrarFormulario = false;
  productoEditando: any = null;

  // Paginado
  paginaActual = 1;
  productosPorPagina = 40;
  totalProductos = 0;
  totalPaginas = 0;

  // Filtros de lista
  filtroCategoria: number | null = null;
  filtroSubcategoria: number | null = null;
  filtroSubsubcategoria: number | null = null;
  filtroEstadoStock: string = '';  // '', 'disponible', 'bajo', 'no_disponible'
  filtroVersion: string = '';
  ordenarPor: string = 'nuevo';
  filtroBusqueda = '';

  // Listas para desplegables de filtros en cascada
  subcategoriasDisponibles: any[] = [];
  subsubcategoriasDisponibles: any[] = [];

  nuevoProducto: any = {
    nombre: '',
    descripcion: '',
    precio_base: 0,
    precio_descuento: null,
    categoria_id: null as number | null,
    activo: null as boolean | null,
    destacado: false,
    color: '',
    color_hex: '',
    producto_relacionado_id: null as number | null,
    dorsal: '',
    numero: null,
    version: '',
    productos_relacionados: [] as number[]
  };

  imagenesSeleccionadas: File[] = [];
  imagenesPreview: string[] = [];
  imagenesExistentes: any[] = [];
  isDragging = false;

  constructor(
    private apiService: ApiService,
    private authService: AuthService,
    private router: Router,
    private cdr: ChangeDetectorRef,
    private zone: NgZone
  ) { }

  // Expo Math para el template
  Math = Math;

  ngOnInit() {
    if (!this.authService.isLoggedIn()) {
      this.router.navigate(['/admin/login']);
      return;
    }
    this.loadProductos();
    this.loadCategorias();
    this.loadTalles();
  }

  tallesDisp: any[] = [];
  loadTalles() {
    this.apiService.getTalles().subscribe(data => {
      this.tallesDisp = data;
    });
  }

  loadProductos() {
    // Solo mostrar loading si no hay datos previos
    if (this.productos.length === 0) {
      this.loading = true;
    }

    const filtros: any = {};
    if (this.filtroCategoria) filtros.categoria_id = this.filtroCategoria;
    if (this.filtroSubcategoria) filtros.subcategoria_id = this.filtroSubcategoria;
    if (this.filtroSubsubcategoria) filtros.subsubcategoria_id = this.filtroSubsubcategoria;
    if (this.filtroEstadoStock) filtros.estado_stock = this.filtroEstadoStock;
    if (this.filtroVersion) filtros.version = this.filtroVersion;
    if (this.ordenarPor) filtros.ordenar_por = this.ordenarPor;
    if (this.filtroBusqueda) filtros.busqueda = this.filtroBusqueda;

    // Paginado
    filtros.page = this.paginaActual;
    filtros.page_size = this.productosPorPagina;
    filtros.activos = false;  // Mostrar todos en admin

    this.apiService.getProductos(filtros).subscribe({
      next: (data) => {
        // Manejar respuesta paginada o array
        if (data.items) {
          // Respuesta paginada del backend
          this.productos = data.items;
          this.totalProductos = data.total || data.items.length;
          this.totalPaginas = Math.ceil(this.totalProductos / this.productosPorPagina);
        } else {
          // Array simple (fallback)
          this.productos = data;
          this.totalProductos = data.length;
          this.totalPaginas = 1;
        }
        this.loading = false;
        this.cdr.detectChanges();
      },
      error: (error) => {
        console.error('Error cargando productos:', error);
        this.loading = false;
        this.cdr.detectChanges();
      }
    });
  }

  filtrarPorCategoria() {
    this.loadProductos();
  }

  buscarProductos() {
    this.loadProductos();
  }

  limpiarFiltros() {
    this.filtroCategoria = null;
    this.filtroSubcategoria = null;
    this.filtroSubsubcategoria = null;
    this.filtroEstadoStock = '';
    this.filtroBusqueda = '';
    this.subcategoriasDisponibles = [];
    this.subsubcategoriasDisponibles = [];
    this.paginaActual = 1;
    this.loadProductos();
  }

  onFiltroCategoriaChange() {
    // Resetear filtros dependientes
    this.filtroSubcategoria = null;
    this.filtroSubsubcategoria = null;
    this.subsubcategoriasDisponibles = [];

    // Cargar subcategorías disponibles basadas en la categoría seleccionada
    if (this.filtroCategoria) {
      this.subcategoriasDisponibles = this.categorias.filter((cat: any) =>
        cat.categoria_padre_id === this.filtroCategoria
      );
    } else {
      this.subcategoriasDisponibles = [];
    }

    this.loadProductos();
  }

  onFiltroSubcategoriaChange() {
    // Resetear filtro de sub-subcategoría
    this.filtroSubsubcategoria = null;

    // Cargar sub-subcategorías disponibles
    if (this.filtroSubcategoria) {
      this.subsubcategoriasDisponibles = this.categorias.filter((cat: any) =>
        cat.categoria_padre_id === this.filtroSubcategoria
      );
    } else {
      this.subsubcategoriasDisponibles = [];
    }

    this.loadProductos();
  }

  loadCategorias() {
    this.apiService.getCategorias(true, undefined, true).subscribe({
      next: (data) => {
        // Normalizar y APLANAR la estructura si viene anidada (por culpa del caché del servicio)
        const allCats: any[] = [];
        const process = (items: any[]) => {
          items.forEach(c => {
            allCats.push({
              ...c,
              id: Number(c.id),
              categoria_padre_id: c.categoria_padre_id ? Number(c.categoria_padre_id) : null
            });
            if (c.subcategorias && c.subcategorias.length > 0) {
              process(c.subcategorias);
            }
          });
        };
        process(Array.isArray(data) ? data : [data]);

        // Guardar lista plana sin 'Ofertas'
        this.categorias = allCats.filter((c: any) => (c.nombre || '').trim().toLowerCase() !== 'ofertas');

        console.log('[DEBUG] Total categorías (aplanadas):', this.categorias.length);

        // La estructura real es: Indumentaria (nivel 1) → Remeras/Shorts (nivel 2)
        this.categoriasPadre = this.categorias.filter((cat: any) => {
          const nombre = (cat.nombre || '').trim().toLowerCase();
          return cat.categoria_padre_id !== null && (nombre === 'remeras' || nombre === 'shorts');
        });

        // Fallback: si no hay con padre, buscar cualquiera con ese nombre
        if (this.categoriasPadre.length === 0) {
          this.categoriasPadre = this.categorias.filter((cat: any) => {
            const nombre = (cat.nombre || '').trim().toLowerCase();
            return nombre === 'remeras' || nombre === 'shorts';
          });
        }

        console.log('[DEBUG] Categorías Padre:', this.categoriasPadre.map(c => `${c.nombre}(${c.id})`));
        
        // IMPORTANTE: Si ya tenemos un producto cargado (Edición), forzar detección de sus subcategorías
        if (this.nuevoProducto.categoria_id) {
          this.detectarJerarquiaDesdeId(this.nuevoProducto.categoria_id);
        }

        this.cdr.detectChanges();
      },
      error: (error) => {
        console.error('Error cargando categorías:', error);
        this.cdr.detectChanges();
      }
    });
  }

  /**
   * Reconstruye la jerarquía de dropdowns a partir de un ID de categoría final
   */
  private detectarJerarquiaDesdeId(id: number) {
    const finalCat = this.categorias.find(c => Number(c.id) === Number(id));
    if (!finalCat) return;

    console.log('[DEBUG] Reconstruyendo jerarquía para:', finalCat.nombre);

    if (finalCat.nivel === 4 || finalCat.nivel === 3) {
      // Es una Liga o una Temporada
      const padre = this.categorias.find(c => Number(c.id) === Number(finalCat.categoria_padre_id));
      if (padre) {
        if (padre.nivel === 3) {
          // finalCat es Nivel 4 (Liga)
          this.subcategoriaNivel1Seleccionada = padre.id;
          this.categoriaPadreSeleccionada = padre.categoria_padre_id;
        } else if (padre.nivel === 2) {
          // finalCat es Nivel 3 (Temporada)
          this.categoriaPadreSeleccionada = padre.id;
          this.subcategoriaNivel1Seleccionada = finalCat.id;
        }
      }
    } else if (finalCat.nivel === 2) {
      this.categoriaPadreSeleccionada = finalCat.id;
    }

    // Ejecutar lógica de carga de hijos
    if (this.categoriaPadreSeleccionada) this.onCategoriaPadreChange();
    if (this.subcategoriaNivel1Seleccionada) this.onSubcategoriaNivel1Change();
    
    // Restaurar el ID original que se borra al resetear
    this.nuevoProducto.categoria_id = id;
  }

  onColorSelected(colorObj: any) {
    if (colorObj && colorObj.name) {
      this.nuevoProducto.color = colorObj.name;
      this.colorSeleccionado = colorObj.hex;
      this.nuevoProducto.color_hex = colorObj.hex;
    }
  }

  getColorByName(name: string): any {
    const colors = [
      { name: 'Rojo', hex: '#FF0000' },
      { name: 'Azul', hex: '#0000FF' },
      { name: 'Verde', hex: '#00FF00' },
      { name: 'Amarillo', hex: '#FFFF00' },
      { name: 'Naranja', hex: '#FFA500' },
      { name: 'Rosa', hex: '#FFC0CB' },
      { name: 'Morado', hex: '#800080' },
      { name: 'Negro', hex: '#000000' },
      { name: 'Blanco', hex: '#FFFFFF' },
      { name: 'Gris', hex: '#808080' },
      { name: 'Marrón', hex: '#A52A2A' },
      { name: 'Dorado', hex: '#FFD700' },
      { name: 'Plateado', hex: '#C0C0C0' },
      { name: 'Turquesa', hex: '#40E0D0' },
      { name: 'Verde Lima', hex: '#32CD32' },
      { name: 'Azul Marino', hex: '#000080' },
      { name: 'Rojo Oscuro', hex: '#8B0000' },
      { name: 'Verde Oscuro', hex: '#006400' },
      { name: 'Azul Cielo', hex: '#87CEEB' },
      { name: 'Coral', hex: '#FF7F50' }
    ];
    return colors.find(c => c.name === name);
  }

  onCategoriaPadreChange() {
    // Normalizar a número
    const selectedId = this.categoriaPadreSeleccionada ? Number(this.categoriaPadreSeleccionada) : null;
    this.categoriaPadreSeleccionada = selectedId;

    // Resetear selecciones de nivel inferior
    this.subcategoriaNivel1Seleccionada = null;
    this.subcategoriasNivel1 = [];
    this.subcategoriasNivel2 = [];
    this.nuevoProducto.categoria_id = null;

    if (selectedId) {
      this.mostrarSubcategorias = true;

      // Usar Number() en ambos lados para evitar fallo por string vs number
      this.subcategoriasNivel1 = this.categorias.filter((cat: any) =>
        Number(cat.categoria_padre_id) === selectedId
      );
      console.log(`[DEBUG] Subcategorias Nivel 1 para ID ${selectedId}:`, this.subcategoriasNivel1.length, this.subcategoriasNivel1.map((c:any)=>c.nombre));

      if (this.subcategoriasNivel1.length === 0) {
        this.nuevoProducto.categoria_id = selectedId;
      }
    } else {
      this.mostrarSubcategorias = false;
    }
    this.cdr.detectChanges();
  }

  onSubcategoriaNivel1Change() {
    // Normalizar a número
    const selectedId = this.subcategoriaNivel1Seleccionada ? Number(this.subcategoriaNivel1Seleccionada) : null;
    this.subcategoriaNivel1Seleccionada = selectedId;

    this.subcategoriasNivel2 = [];
    this.nuevoProducto.categoria_id = null;

    if (selectedId) {
      // Usar Number() en ambos lados para evitar fallo por string vs number
      this.subcategoriasNivel2 = this.categorias.filter((cat: any) =>
        Number(cat.categoria_padre_id) === selectedId
      );

      console.log(`[DEBUG] Subcategorias Nivel 2 para ID ${selectedId}:`, this.subcategoriasNivel2.length, this.subcategoriasNivel2.map((c:any)=>c.nombre));

      if (this.subcategoriasNivel2.length === 0) {
        this.nuevoProducto.categoria_id = selectedId;
      }
    }
    this.cdr.detectChanges();
  }

  nuevo() {
    this.productoEditando = null;
    this.categoriaPadreSeleccionada = null;
    this.subcategoriaNivel1Seleccionada = null;
    this.subcategoriasNivel1 = [];
    this.subcategoriasNivel2 = [];
    this.mostrarSubcategorias = false;
    this.colorSeleccionado = '';
    this.productoRelacionadoId = null;
    this.nuevoProducto = {
      nombre: '',
      descripcion: '',
      precio_base: 0,
      precio_descuento: null,
      categoria_id: null as number | null,
      activo: null as boolean | null,
      destacado: false,
      color: '',
      color_hex: '',
      producto_relacionado_id: null,
      dorsal: '',
      numero: null,
      version: ''
    };
    this.imagenesSeleccionadas = [];
    this.imagenesPreview = [];
    this.imagenesExistentes = [];
    this.mostrarFormulario = true;
  }

  editar(producto: any) {
    this.productoEditando = producto;
    this.loading = true; // Bloquear UI

    this.apiService.getProducto(producto.id).subscribe({
      next: (fullProducto) => {
        this.loading = false;
        const productoFrescos = fullProducto;

        // --- LÓGICA DE CATEGORÍAS (Usando datos frescos) ---
        const categoriaProducto = this.categorias.find((c: any) => c.id === productoFrescos.categoria_id);

        if (categoriaProducto) {
          if (categoriaProducto.categoria_padre_id) {
            const categoriaNivel1 = this.categorias.find((c: any) => c.id === categoriaProducto.categoria_padre_id);

            if (categoriaNivel1 && categoriaNivel1.categoria_padre_id) {
              this.categoriaPadreSeleccionada = categoriaNivel1.categoria_padre_id;
              this.onCategoriaPadreChange();
              this.subcategoriaNivel1Seleccionada = categoriaNivel1.id;
              this.onSubcategoriaNivel1Change();
              this.nuevoProducto.categoria_id = productoFrescos.categoria_id;
            } else if (categoriaNivel1) {
              this.categoriaPadreSeleccionada = categoriaNivel1.id;
              this.onCategoriaPadreChange();
              this.subcategoriaNivel1Seleccionada = productoFrescos.categoria_id;
              this.onSubcategoriaNivel1Change();
            }
          } else {
            this.categoriaPadreSeleccionada = productoFrescos.categoria_id;
            this.subcategoriasNivel1 = [];
            this.subcategoriasNivel2 = [];
            this.mostrarSubcategorias = false;
            this.nuevoProducto.categoria_id = productoFrescos.categoria_id;
          }
        }

        this.colorSeleccionado = productoFrescos.color_hex || '';
        this.productoRelacionadoId = productoFrescos.producto_relacionado_id || null;

        this.nuevoProducto = {
          nombre: productoFrescos.nombre,
          descripcion: productoFrescos.descripcion || '',
          precio_base: productoFrescos.precio_base,
          precio_descuento: productoFrescos.precio_descuento,
          categoria_id: productoFrescos.categoria_id,
          activo: productoFrescos.activo,
          destacado: productoFrescos.destacado,
          color: productoFrescos.color || '',
          color_hex: productoFrescos.color_hex || '',
          producto_relacionado_id: productoFrescos.producto_relacionado_id || null,
          dorsal: productoFrescos.dorsal || '',
          numero: productoFrescos.numero || null,
          version: productoFrescos.version || '',
          productos_relacionados: []
        };

        // Cargar productos relacionados (con datos frescos)
        // La propiedad en to_dict es 'relacionados', en create es 'productos_relacionados'
        if (productoFrescos.relacionados && Array.isArray(productoFrescos.relacionados)) {
          this.productosRelacionadosSeleccionados = [...productoFrescos.relacionados];
        } else {
          this.productosRelacionadosSeleccionados = [];
        }

        this.imagenesSeleccionadas = [];
        this.imagenesPreview = [];
        this.imagenesExistentes = (productoFrescos.imagenes || []).sort((a: any, b: any) => (a.orden || 0) - (b.orden || 0));
        this.mostrarFormulario = true;
        this.cdr.detectChanges(); // Forzar actualización de vista
      },
      error: (err) => {
        this.loading = false;
        Swal.fire('Error', 'No se pudieron cargar los detalles del producto.', 'error');
        console.error(err);
      }
    });

  }

  guardar() {
    // Convertir valores string a number
    if (typeof this.categoriaPadreSeleccionada === 'string' && this.categoriaPadreSeleccionada !== '') {
      this.categoriaPadreSeleccionada = parseInt(this.categoriaPadreSeleccionada);
    }
    if (typeof this.nuevoProducto.categoria_id === 'string' && this.nuevoProducto.categoria_id !== '') {
      this.nuevoProducto.categoria_id = parseInt(this.nuevoProducto.categoria_id as unknown as string);
    }

    // Si no hay subcategorías, usar la categoría padre
    if (!this.nuevoProducto.categoria_id && this.categoriaPadreSeleccionada) {
      this.nuevoProducto.categoria_id = this.categoriaPadreSeleccionada as number;
    }

    // Asignar lista de productos relacionados
    this.nuevoProducto.productos_relacionados = this.productosRelacionadosSeleccionados.map(p => p.id);

    // Mantener compatibilidad legacy temporal (usar el primero como principal si se quiere)
    if (this.productosRelacionadosSeleccionados.length > 0) {
      this.nuevoProducto.producto_relacionado_id = this.productosRelacionadosSeleccionados[0].id;
    } else {
      this.nuevoProducto.producto_relacionado_id = null;
    }

    if (!this.nuevoProducto.nombre || !this.nuevoProducto.precio_base || this.nuevoProducto.precio_base <= 0 || !this.nuevoProducto.categoria_id) {
      Swal.fire({
        title: 'Campos incompletos',
        text: 'Por favor completa todos los campos requeridos (Nombre, Precio Base y Categoría)',
        icon: 'warning'
      });
      return;
    }

    if (this.productoEditando) {
      // Actualizar producto
      Swal.fire({ title: 'Actualizando producto...', allowOutsideClick: false, didOpen: () => { Swal.showLoading(); } });
      this.apiService.updateProducto(this.productoEditando.id, this.nuevoProducto).subscribe({
        next: (productoActualizado) => {
          // Subir imágenes si hay nuevas
          if (this.imagenesSeleccionadas.length > 0) {
            this.subirImagenes(productoActualizado.id);
          } else {
            this.loadProductos();
            this.cancelar();
            Swal.fire('¡Éxito!', 'Producto actualizado exitosamente', 'success');
          }
        },
        error: (error) => {
          const mensaje = error.error?.error || error.message || 'Error al actualizar producto';
          Swal.fire('Error', mensaje, 'error');
          console.error('Error completo:', error);
        }
      });
    } else {
      // Crear nuevo producto
      Swal.fire({ title: 'Creando producto...', allowOutsideClick: false, didOpen: () => { Swal.showLoading(); } });
      this.apiService.createProducto(this.nuevoProducto).subscribe({
        next: (nuevoProducto) => {
          // Subir imágenes si hay
          if (this.imagenesSeleccionadas.length > 0) {
            this.subirImagenes(nuevoProducto.id);
          } else {
            this.loadProductos();
            this.cancelar();
            Swal.fire('¡Éxito!', 'Producto creado exitosamente', 'success');
          }
        },
        error: (error) => {
          const mensaje = error.error?.error || error.message || 'Error desconocido';
          Swal.fire('Error', mensaje, 'error');
          console.error('Error completo:', error);
        }
      });
    }
  }

  subirImagenes(productoId: number) {
    let imagenesSubidas = 0;
    const totalImagenes = this.imagenesSeleccionadas.length;

    if (totalImagenes === 0) {
      this.loadProductos();
      this.cancelar();
      return;
    }

    this.imagenesSeleccionadas.forEach((file, index) => {
      const esPrincipal = index === 0;
      this.apiService.uploadImagen(productoId, file, esPrincipal, index).subscribe({
        next: () => {
          imagenesSubidas++;
          if (imagenesSubidas === totalImagenes) {
            this.loadProductos();
            this.cancelar();
            Swal.fire('¡Hecho!', 'Producto ' + (this.productoEditando ? 'actualizado' : 'creado') + ' e imágenes subidas correctamente', 'success');
          }
        },
        error: (error) => {
          console.error('Error subiendo imagen:', error);
          imagenesSubidas++;
          if (imagenesSubidas === totalImagenes) {
            this.loadProductos();
            this.cancelar();
            Swal.fire('Aviso', 'Producto ' + (this.productoEditando ? 'actualizado' : 'creado') + ' pero hubo errores al cargar algunas imágenes', 'info');
          }
        }
      });
    });
  }

  onFileSelected(event: any) {
    const files = Array.from(event.target.files) as File[];
    this.procesarArchivos(files);
  }

  onDragOver(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging = true;
  }

  onDragLeave(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging = false;
  }

  onFileDropped(event: DragEvent) {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging = false;

    if (event.dataTransfer && event.dataTransfer.files.length > 0) {
      const files = Array.from(event.dataTransfer.files) as File[];
      this.procesarArchivos(files);
    }
  }

  procesarArchivos(files: File[]) {
    // Filtrar solo imágenes
    const imageFiles = files.filter(file => file.type.startsWith('image/'));
    
    this.imagenesSeleccionadas = [...this.imagenesSeleccionadas, ...imageFiles];

    imageFiles.forEach(file => {
      const reader = new FileReader();
      reader.onload = (e: any) => {
        this.zone.run(() => {
          this.imagenesPreview.push(e.target.result);
          this.cdr.detectChanges();
        });
      };
      reader.readAsDataURL(file);
    });
  }

  moverImagenPreview(index: number, direction: number) {
    const newIndex = index + direction;
    if (newIndex >= 0 && newIndex < this.imagenesPreview.length) {
      // Intercambiar en previews
      const tempPreview = this.imagenesPreview[index];
      this.imagenesPreview[index] = this.imagenesPreview[newIndex];
      this.imagenesPreview[newIndex] = tempPreview;

      // Intercambiar en archivos
      const tempFile = this.imagenesSeleccionadas[index];
      this.imagenesSeleccionadas[index] = this.imagenesSeleccionadas[newIndex];
      this.imagenesSeleccionadas[newIndex] = tempFile;

      this.cdr.detectChanges();
    }
  }

  eliminarImagenPreview(index: number) {
    this.imagenesPreview.splice(index, 1);
    this.imagenesSeleccionadas.splice(index, 1);
  }

  setImagenPrincipal(imagen: any) {
    if (imagen.es_principal) return;

    this.apiService.updateImagen(imagen.id, { es_principal: true }).subscribe({
      next: () => {
        this.imagenesExistentes.forEach(img => img.es_principal = (img.id === imagen.id));
        this.loadProductos();
        this.cdr.detectChanges();
      },
      error: (err) => {
        Swal.fire('Error', 'No se pudo establecer como imagen principal.', 'error');
      }
    });
  }

  moverImagenExistente(index: number, direction: number) {
    const newIndex = index + direction;
    if (newIndex >= 0 && newIndex < this.imagenesExistentes.length) {
      const imgTarget = this.imagenesExistentes[index];
      const imgSwap = this.imagenesExistentes[newIndex];

      // Swap orden
      const oldOrden = imgTarget.orden || 0;
      imgTarget.orden = imgSwap.orden || 0;
      imgSwap.orden = oldOrden;

      // Swap in array
      this.imagenesExistentes[index] = imgSwap;
      this.imagenesExistentes[newIndex] = imgTarget;

      // Sync backend
      this.apiService.updateImagen(imgTarget.id, { orden: imgTarget.orden }).subscribe();
      this.apiService.updateImagen(imgSwap.id, { orden: imgSwap.orden }).subscribe();

      this.cdr.detectChanges();
    }
  }

  eliminarImagenExistente(imagenId: number) {
    Swal.fire({
      title: '¿Eliminar imagen?',
      text: 'Esta acción no se puede deshacer',
      icon: 'warning',
      showCancelButton: true,
      confirmButtonText: 'Sí, eliminar',
      cancelButtonText: 'Cancelar'
    }).then((result) => {
      if (result.isConfirmed) {
        this.apiService.deleteImagen(imagenId).subscribe({
          next: () => {
            this.imagenesExistentes = this.imagenesExistentes.filter(img => img.id !== imagenId);
            this.loadProductos();
            Swal.fire('Eliminada', 'La imagen ha sido eliminada', 'success');
          },
          error: (error) => {
            Swal.fire('Error', 'No se pudo eliminar la imagen', 'error');
            console.error(error);
          }
        });
      }
    });
  }

  eliminar(producto: any) {
    Swal.fire({
      title: '¿Estás seguro?',
      text: `Vas a eliminar "${producto.nombre}". Esta acción no siempre se puede deshacer.`,
      icon: 'warning',
      showCancelButton: true,
      confirmButtonColor: '#d33',
      cancelButtonColor: '#3085d6',
      confirmButtonText: 'Sí, eliminar',
      cancelButtonText: 'Cancelar',
      reverseButtons: true
    }).then((result) => {
      if (result.isConfirmed) {
        // --- UI OPTIMISTA: Borrar de la lista local inmediatamente ---
        const index = this.productos.findIndex(p => p.id === producto.id);
        if (index > -1) {
          const productoCopia = { ...this.productos[index] };
          this.productos.splice(index, 1);
          this.totalProductos--;
          this.cdr.detectChanges();

          this.apiService.deleteProducto(producto.id).subscribe({
            next: () => {
              Swal.fire({
                title: 'Eliminado',
                text: `Producto "${producto.nombre}" eliminado exitosamente`,
                icon: 'success',
                timer: 1500,
                showConfirmButton: false
              });
              // Recargar para sincronizar paginado y totales exactamente
              this.loadProductos();
            },
            error: (error) => {
              // --- ROLLBACK: Si falla, lo devolvemos a la lista ---
              this.productos.splice(index, 0, productoCopia);
              this.totalProductos++;
              this.cdr.detectChanges();

            const errorData = error.error;
            if (errorData && errorData.suggestion === 'desactivar') {
              Swal.fire({
                title: 'No se puede eliminar',
                text: `${errorData.error}`,
                icon: 'info',
                showCancelButton: true,
                confirmButtonText: 'Desactivar producto',
                cancelButtonText: 'Entendido'
              }).then((res) => {
                if (res.isConfirmed) {
                  this.apiService.updateProducto(producto.id, { activo: false }).subscribe({
                    next: () => {
                      producto.activo = false;
                      Swal.fire('Desactivado', 'El producto ha sido desactivado.', 'success');
                      this.loadProductos();
                    },
                    error: (err) => {
                      Swal.fire('Error', 'No se pudo desactivar el producto.', 'error');
                    }
                  });
                }
              });
            } else {
              Swal.fire('Error', errorData?.error || 'No se pudo eliminar el producto.', 'error');
            }
          }
        });
      }
    }
  });
}

  // --- MÉTODOS DE SELECCIÓN MÚLTIPLE ---
  
  toggleSeleccion(id: number) {
    const index = this.productosSeleccionados.indexOf(id);
    if (index > -1) {
      this.productosSeleccionados.splice(index, 1);
    } else {
      this.productosSeleccionados.push(id);
    }
  }

  isSeleccionado(id: number): boolean {
    return this.productosSeleccionados.includes(id);
  }

  toggleTodos() {
    if (this.productosSeleccionados.length === this.productos.length) {
      this.productosSeleccionados = [];
    } else {
      this.productosSeleccionados = this.productos.map(p => p.id);
    }
  }

  eliminarSeleccionados() {
    if (this.productosSeleccionados.length === 0) return;

    Swal.fire({
      title: '¿Eliminar seleccionados?',
      text: `Vas a eliminar ${this.productosSeleccionados.length} productos. Los que tengan pedidos asociados no serán borrados por seguridad.`,
      icon: 'warning',
      showCancelButton: true,
      confirmButtonColor: '#d33',
      confirmButtonText: 'Sí, eliminar todos',
      cancelButtonText: 'Cancelar'
    }).then((result) => {
      if (result.isConfirmed) {
        this.procesandoBulk = true;
        const idsABorrar = [...this.productosSeleccionados];
        
        // UI OPTIMISTA: Borrar localmente
        const backupProductos = [...this.productos];
        this.productos = this.productos.filter(p => !idsABorrar.includes(p.id));
        this.productosSeleccionados = [];
        this.cdr.detectChanges();

        // Mostrar cargando inmediato mientras se procesa el bulk
        Swal.fire({
          title: 'Eliminando productos...',
          text: 'Por favor espera un momento',
          allowOutsideClick: false,
          didOpen: () => {
            Swal.showLoading();
          }
        });

        this.apiService.deleteProductosBulk(idsABorrar).subscribe({
          next: (res) => {
            this.procesandoBulk = false;
            let msg = `Se eliminaron ${res.eliminados.length} productos. `;
            if (res.errores.length > 0) {
              msg += `${res.errores.length} fallaron por tener dependencias.`;
            }
            
            Swal.fire({
              title: '¡Operación finalizada!',
              text: msg,
              icon: res.errores.length > 0 ? 'info' : 'success',
              confirmButtonText: 'Genial'
            });
            this.loadProductos(); // Recargar para sincronizar exacto
          },
          error: (err) => {
            this.procesandoBulk = false;
            this.productos = backupProductos; // Rollback
            Swal.fire('Error', 'Hubo un fallo crítico al procesar la eliminación.', 'error');
            this.cdr.detectChanges();
          }
        });
      }
    });
  }

  cancelar() {
    this.mostrarFormulario = false;
    this.productoEditando = null;
    this.productosRelacionadosSeleccionados = []; // RESETEAR LISTA
    this.nuevoProducto = {
      nombre: '',
      descripcion: '',
      precio_base: 0,
      precio_descuento: null,
      categoria_id: null,
      activo: null,
      destacado: false,
      color: '',
      color_hex: '',
      producto_relacionado_id: null,
      dorsal: '',
      numero: null,
      version: '',
      productos_relacionados: []
    };
  }

  getImagenPrincipal(producto: any): string {
    if (producto.imagenes && producto.imagenes.length > 0) {
      const principal = producto.imagenes.find((img: any) => img.es_principal);
      if (principal) return this.apiService.getFormattedImageUrl(principal.url);
      return this.apiService.getFormattedImageUrl(producto.imagenes[0].url);
    }
    return "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='150' height='150'%3E%3Crect fill='%23ddd' width='150' height='150'/%3E%3Ctext x='50%25' y='50%25' text-anchor='middle' dy='.3em' font-family='sans-serif' font-size='14' fill='%23999'%3ESin imagen%3C/text%3E%3C/svg%3E";
  }

  getFormattedImageUrl(url: string | null | undefined): string {
    return this.apiService.getFormattedImageUrl(url);
  }

  // --- MÉTODOS PARA PRODUCTO RELACIONADO (AUTOCOMPLETE) ---
  buscandoRelacionados = false; // Nueva variable de estado local

  buscarProductoRelacionado() {
    if (!this.busquedaProductoRelacionado || this.busquedaProductoRelacionado.length < 2) {
      this.productosRelacionadosFiltrados = [];
      return;
    }

    const termino = this.busquedaProductoRelacionado;
    this.buscandoRelacionados = true;

    // Usar endpoint optimizado para búsqueda (trae ID, nombre, color, hex)
    this.apiService.searchProducts(termino).subscribe({
      next: (data) => {
        // Data puede ser array o objeto paginado
        const items = Array.isArray(data) ? data : (data.items || []);

        this.productosRelacionadosFiltrados = items.filter((p: any) =>
          p.id !== this.nuevoProducto.id && // No mostrarse a sí mismo
          (!this.productoEditando || p.id !== this.productoEditando.id)
        );
        this.buscandoRelacionados = false;
        this.cdr.detectChanges();
      },
      error: (err) => {
        console.error('Error buscando productos:', err);
        this.buscandoRelacionados = false;
      }
    });

    // Fallback local removido para garantizar consistencia global
  }

  seleccionarProductoRelacionado(producto: any) {
    if (!this.productosRelacionadosSeleccionados.some(p => p.id === producto.id)) {
      this.productosRelacionadosSeleccionados.push(producto);
    }
    this.busquedaProductoRelacionado = '';
    this.productosRelacionadosFiltrados = [];
  }

  removerProductoRelacionado(index: number) {
    this.productosRelacionadosSeleccionados.splice(index, 1);
  }

  limpiarProductoRelacionado() {
    this.nuevoProducto.producto_relacionado_id = null;
    this.busquedaProductoRelacionado = '';
    this.productosRelacionadosFiltrados = [];
  }

  // --- AUTOCOMPLETE NOMBRE ---
  sugerenciasNombre: any[] = [];

  buscarSugerenciasNombre() {
    const termino = this.nuevoProducto.nombre;
    if (!termino || termino.length < 3) {
      this.sugerenciasNombre = [];
      return;
    }

    // Usar la misma API search
    this.apiService.searchProducts(termino).subscribe({
      next: (data) => {
        const items = Array.isArray(data) ? data : (data.items || []);
        // Filtrar nombres únicos para no repetir
        const nombresUnicos = new Set();
        this.sugerenciasNombre = items.filter((p: any) => {
          if (nombresUnicos.has(p.nombre)) return false;
          nombresUnicos.add(p.nombre);
          return true;
        });
      }
    });
  }

  seleccionarNombreSugerido(nombre: string) {
    this.nuevoProducto.nombre = nombre;
    this.sugerenciasNombre = []; // Ocultar sugerencias
  }

  getCleanCategoryPath(catId: number | null, pathNodes: number[] = []): string {
    if (!catId) return '';

    // Evitar recursión infinita
    if (pathNodes.includes(catId)) {
      return '';
    }

    const cat = this.categorias.find(c => Number(c.id) === Number(catId));
    if (!cat) return '';

    if (!cat.categoria_padre_id) {
      return cat.nombre;
    }

    const padre = this.categorias.find(p => Number(p.id) === Number(cat.categoria_padre_id));
    if (padre && padre.id !== catId) {
      return `${this.getCleanCategoryPath(padre.id, [...pathNodes, catId])} > ${cat.nombre}`;
    }

    return cat.nombre;
  }

  getCategoryPath(catId: number | null): string {
    if (!catId) return '-';

    // Obtenemos el path sin iconos
    const path = this.getCleanCategoryPath(catId);

    // Verificamos si es una categoría principal para poner el icono
    const cat = this.categorias.find(c => c.id === catId);
    if (cat && !cat.categoria_padre_id) {
      return `🏠 ${path}`;
    }

    return path || '-';
  }

  // Métodos de paginado
  cambiarPagina(pagina: number) {
    if (pagina >= 1 && pagina <= this.totalPaginas) {
      this.paginaActual = pagina;
      this.loadProductos();
      window.scrollTo(0, 0);
    }
  }

  siguientePagina() {
    this.cambiarPagina(this.paginaActual + 1);
  }

  anteriorPagina() {
    this.cambiarPagina(this.paginaActual - 1);
  }

  getPaginasArray(): number[] {
    const paginas: number[] = [];
    const maxBotones = 5; // Mostrar máximo 5 botones de página

    let inicio = Math.max(1, this.paginaActual - Math.floor(maxBotones / 2));
    let fin = Math.min(this.totalPaginas, inicio + maxBotones - 1);

    // Ajustar si estamos cerca del final
    if (fin - inicio < maxBotones - 1) {
      inicio = Math.max(1, fin - maxBotones + 1);
    }

    for (let i = inicio; i <= fin; i++) {
      paginas.push(i);
    }

    return paginas;
  }

  formatPrecio(precio: number): string {
    if (!precio && precio !== 0) return '0';
    return precio.toLocaleString('es-AR', { minimumFractionDigits: 0, maximumFractionDigits: 0 });
  }

  async abrirModalBulkStock() {
    if (this.productosSeleccionados.length === 0) {
      Swal.fire('Atención', 'Selecciona al menos un producto de la lista.', 'info');
      return;
    }

    const idsString = this.productosSeleccionados.join(',');
    this.router.navigate(['/admin/stock'], { 
      queryParams: { producto_ids: idsString } 
    });
  }
}

