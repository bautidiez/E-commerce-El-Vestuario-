import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterModule, Router } from '@angular/router';
import { ApiService } from '../../../services/api.service';
import { AuthService } from '../../../services/auth.service';
import Swal from 'sweetalert2';

interface Categoria {
    id?: number;
    nombre: string;
    descripcion: string;
    imagen?: string;
    orden: number;
    categoria_padre_id?: number | null;
    activa: boolean;
    nivel?: number;
    subcategorias?: Categoria[];
}

@Component({
    selector: 'app-categorias-admin',
    imports: [CommonModule, FormsModule, RouterModule],
    templateUrl: './categorias-admin.html',
    styleUrl: './categorias-admin.css'
})
export class CategoriasAdminComponent implements OnInit {
    categorias: Categoria[] = [];
    arbolCategorias: Categoria[] = [];
    mostrarFormulario = false;
    modoEdicion = false;
    cargandoCategorias = true;  // Estado de carga

    categoriaActual: Categoria = this.nuevaCategoria();

    // Wizard steps
    pasoActual = 1;
    totalPasos = 3;

    // Datos para subcategorías
    categoriasDisponibles: Categoria[] = []; // Para selección de padre
    nuevasSubcategorias: Partial<Categoria>[] = [];

    // Vista
    vistaActual: 'lista' | 'arbol' = 'arbol';
    expandidos: Set<number> = new Set();

    constructor(
        private apiService: ApiService,
        private authService: AuthService,
        private router: Router,
        private cdr: ChangeDetectorRef
    ) { }

    ngOnInit() {
        if (!this.authService.isLoggedIn()) {
            this.router.navigate(['/admin/login']);
            return;
        }
        this.loadCategorias();
        this.loadArbolCategorias();
    }

    nuevaCategoria(): Categoria {
        return {
            nombre: '',
            descripcion: '',
            orden: 0,
            activa: true,
            categoria_padre_id: null
        };
    }

    loadCategorias() {
        this.cargandoCategorias = true;
        this.apiService.getCategorias(true, undefined, true).subscribe({
            next: (data: Categoria[]) => {
                // Asegurar que los IDs sean números
                this.categorias = data.map(c => ({
                    ...c,
                    id: Number(c.id),
                    categoria_padre_id: c.categoria_padre_id ? Number(c.categoria_padre_id) : null
                }));

                // Todas las categorías pueden ser candidatas a padre si nivel < 3
                this.categoriasDisponibles = this.categorias.filter(c => (c.nivel || 1) < 3);

                // Luego ordenamos según la ruta completa
                this.categoriasDisponibles.sort((a, b) => {
                    const labelA = this.getCategoriaPadreLabel(a);
                    const labelB = this.getCategoriaPadreLabel(b);
                    return labelA.localeCompare(labelB);
                });
                this.cargandoCategorias = false;
                this.cdr.detectChanges();
            },
            error: (error: any) => {
                console.error('Error al cargar categorías:', error);
                Swal.fire('Error', 'No se pudieron cargar las categorías', 'error');
                this.cargandoCategorias = false;
                this.cdr.detectChanges();
            }
        });
    }

    loadArbolCategorias() {
        this.cargandoCategorias = true;
        this.apiService.get('/categorias/tree').subscribe({
            next: (data: Categoria[]) => {
                this.arbolCategorias = data;
                this.cargandoCategorias = false;
                this.cdr.detectChanges();
            },
            error: (error: any) => {
                console.error('Error al cargar árbol:', error);
                this.cargandoCategorias = false;
                this.cdr.detectChanges();
            }
        });
    }

    nueva() {
        this.categoriaActual = this.nuevaCategoria();
        this.nuevasSubcategorias = [];
        this.pasoActual = 1;
        this.modoEdicion = false;
        this.mostrarFormulario = true;
    }

    editar(categoria: Categoria) {
        this.categoriaActual = { ...categoria };
        this.modoEdicion = true;
        this.pasoActual = 1;
        this.mostrarFormulario = true;
    }

    siguientePaso() {
        if (this.pasoActual < this.totalPasos) {
            this.pasoActual++;
        }
    }

    pasoAnterior() {
        if (this.pasoActual > 1) {
            this.pasoActual--;
        }
    }

    agregarNuevaSubcategoria() {
        this.nuevasSubcategorias.push({
            nombre: '',
            descripcion: '',
            orden: this.nuevasSubcategorias.length,
            activa: true
        });
    }

    eliminarNuevaSubcategoria(index: number) {
        this.nuevasSubcategorias.splice(index, 1);
    }

    guardar() {
        if (!this.categoriaActual.nombre.trim()) {
            Swal.fire({
                toast: true,
                position: 'top-end',
                icon: 'warning',
                title: 'El nombre es requerido',
                showConfirmButton: false,
                timer: 2000
            });
            return;
        }

        const payload: any = {
            nombre: this.categoriaActual.nombre,
            descripcion: this.categoriaActual.descripcion,
            imagen: this.categoriaActual.imagen,
            orden: this.categoriaActual.orden,
            categoria_padre_id: this.categoriaActual.categoria_padre_id,
            activa: this.categoriaActual.activa
        };

        // Agregar nuevas subcategorías
        if (this.nuevasSubcategorias.length > 0) {
            payload.subcategorias_nuevas = this.nuevasSubcategorias.filter(s => s.nombre && s.nombre.trim());
        }

        const request = this.modoEdicion
            ? this.apiService.put(`/admin/categorias/${this.categoriaActual.id}`, payload)
            : this.apiService.post('/admin/categorias', payload);

        request.subscribe({
            next: (data: any) => {
                Swal.fire({
                    icon: 'success',
                    title: this.modoEdicion ? 'Actualizada' : 'Creada',
                    text: this.modoEdicion ? 'La categoría se ha actualizado correctamente' : 'La categoría se ha creado exitosamente',
                    timer: 2000,
                    showConfirmButton: false
                });
                this.cancelar();
                this.loadCategorias();
                this.loadArbolCategorias();
            },
            error: (error: any) => {
                console.error('Error al guardar:', error);
                Swal.fire('Error', error.error?.error || 'No se pudo guardar la categoría', 'error');
            }
        });
    }

    async eliminar(categoria: Categoria) {
        const result = await Swal.fire({
            title: '¿Eliminar categoría?',
            text: `¿Estás seguro de que deseas eliminar "${categoria.nombre}"?`,
            icon: 'warning',
            showCancelButton: true,
            confirmButtonColor: '#d33',
            confirmButtonText: 'Sí, eliminar',
            cancelButtonText: 'Cancelar'
        });

        if (!result.isConfirmed) return;

        this.apiService.deleteCategoria(categoria.id!).subscribe({
            next: () => {
                Swal.fire({
                    toast: true,
                    position: 'top-end',
                    icon: 'success',
                    title: 'Categoría eliminada',
                    showConfirmButton: false,
                    timer: 2000
                });
                this.loadCategorias();
                this.loadArbolCategorias();
            },
            error: async (error: any) => {
                if (error.status === 400 && error.error?.error?.includes('producto(s) asociado(s)')) {
                    const result = await Swal.fire({
                        title: 'Categoría con productos',
                        text: `${error.error.error}. ¿Deseas ELIMINAR TODO (categoría y sus productos) permanentemente?`,
                        icon: 'warning',
                        showCancelButton: true,
                        confirmButtonColor: '#d33',
                        confirmButtonText: 'Sí, ELIMINAR TODO',
                        cancelButtonText: 'Cancelar'
                    });
                    
                    if (result.isConfirmed) {
                        this.forceDelete(categoria.id!);
                    }
                } else {
                    console.error('Error al eliminar:', error);
                    Swal.fire('Error', error.error?.error || 'No se pudo eliminar la categoría', 'error');
                }
            }
        });
    }

    forceDelete(id: number) {
        this.apiService.deleteCategoria(id, true).subscribe({
            next: (response: any) => {
                Swal.fire('Eliminado', response.message || 'La categoría y sus productos han sido eliminados', 'success');
                this.loadCategorias();
                this.loadArbolCategorias();
            },
            error: (error: any) => {
                console.error('Error al forzar eliminación:', error);
                Swal.fire('Error', 'Error crítico al intentar eliminar todo', 'error');
            }
        });
    }

    cancelar() {
        this.mostrarFormulario = false;
        this.categoriaActual = this.nuevaCategoria();
        this.nuevasSubcategorias = [];
        this.pasoActual = 1;
    }

    toggleExpand(id: number) {
        if (this.expandidos.has(id)) {
            this.expandidos.delete(id);
        } else {
            this.expandidos.add(id);
        }
    }

    isExpandido(id: number): boolean {
        return this.expandidos.has(id);
    }

    getNivelClass(nivel: number): string {
        return nivel === 1 ? 'nivel-1' : nivel === 2 ? 'nivel-2' : 'nivel-3';
    }

    getCategoriaPadreNombre(categoriaPadreId: number | null | undefined): string {
        if (!categoriaPadreId) return '-';
        const padre = this.categorias.find(c => c.id === categoriaPadreId);
        return padre ? padre.nombre : '-';
    }

    getCleanCategoryPath(cat: Categoria, pathNodes: number[] = []): string {
        if (!cat.id) return cat.nombre;

        // Evitar recursión infinita
        if (pathNodes.includes(cat.id)) {
            return cat.nombre;
        }

        if (!cat.categoria_padre_id) return cat.nombre;

        const padre = this.categorias.find(c => Number(c.id) === Number(cat.categoria_padre_id));
        if (padre && padre.id !== cat.id) {
            return `${this.getCleanCategoryPath(padre, [...pathNodes, cat.id])} > ${cat.nombre}`;
        }

        return cat.nombre;
    }

    getCategoriaPadreLabel(cat: Categoria): string {
        // Obtenemos el path sin iconos primero
        const path = this.getCleanCategoryPath(cat);
        // Solo agregamos el icono si es una categoría principal (sin padre)
        return !cat.categoria_padre_id ? `🏠 ${path}` : path;
    }

    getCategoriaActualNivel(): number {
        if (!this.categoriaActual.categoria_padre_id) return 1;

        const padre = this.categorias.find(c => c.id === this.categoriaActual.categoria_padre_id);
        if (!padre) return 1;

        return (padre.nivel || 1) + 1;
    }

    volverAlPanel() {
        this.router.navigate(['/admin/gestion']);
    }

    async fixSequences() {
        const result = await Swal.fire({
            title: 'Sincronizar IDs',
            text: '¿Deseas sincronizar los IDs de la base de datos? Esto soluciona el error de "ID duplicado" al crear categorías.',
            icon: 'question',
            showCancelButton: true,
            confirmButtonText: 'Sí, sincronizar',
            cancelButtonText: 'Cancelar'
        });

        if (!result.isConfirmed) return;

        this.apiService.fixSequences().subscribe({
            next: (res) => {
                Swal.fire('Sincronizado', 'Sincronización completada con éxito. Ya puedes intentar crear la categoría.', 'success');
                this.loadCategorias();
            },
            error: (err) => {
                console.error('Error al sincronizar:', err);
                Swal.fire('Error', 'Hubo un error al sincronizar: ' + (err.error?.error || err.message), 'error');
            }
        });
    }
}
