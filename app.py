"""Interfaz gráfica para generar cartas solares."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk

from carta_solar.branding import AUTHORS, CREDIT_LINE, INSTITUTION, available_logos
from carta_solar.config import CartaSolarConfig
from carta_solar.critical import (
    DEFAULT_CRITICAL_MONTHS,
    MONTH_NAMES,
    collect_critical_samples,
    compute_noon_alpha,
    format_exposure_report,
)
from carta_solar.overhang import apply_computed_mask, overhang_projection
from carta_solar.plot import (
    build_output_basename,
    generate_carta_solar,
    save_carta_solar,
    save_carta_solar_to_path,
)


class CartaSolarApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Carta Solar — Aleros Norte")
        self.geometry("1320x860")
        self.minsize(1150, 750)

        self._figure: plt.Figure | None = None
        self._canvas: FigureCanvasTkAgg | None = None
        self._toolbar: NavigationToolbar2Tk | None = None
        self._month_vars: dict[int, tk.BooleanVar] = {}

        self._build_form()
        self._build_preview_panel()
        self._build_status_bar()
        self._bind_shortcuts()

    def _build_form(self) -> None:
        outer = ttk.Frame(self)
        outer.pack(side=tk.LEFT, fill=tk.Y, padx=(10, 0), pady=10)

        canvas = tk.Canvas(outer, width=330, highlightthickness=0)
        scrollbar = ttk.Scrollbar(outer, orient=tk.VERTICAL, command=canvas.yview)
        form_frame = ttk.Frame(canvas)
        form_frame.bind(
            "<Configure>",
            lambda _e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=form_frame, anchor=tk.NW)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side=tk.LEFT, fill=tk.Y)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.site_name_var = tk.StringVar(value="Ñacuñán")
        self.lat_var = tk.StringVar(value="-34.0333")
        self.lon_var = tk.StringVar(value="-67.9167")
        self.hour_start_var = tk.StringVar(value="5")
        self.hour_end_var = tk.StringVar(value="19")
        self.output_dir_var = tk.StringVar(value=str(Path("salida").resolve()))
        self.sill_height_var = tk.StringVar(value="0.9")
        self.window_height_var = tk.StringVar(value="1.2")
        self.gap_to_overhang_var = tk.StringVar(value="0.3")
        self.critical_hour_start_var = tk.StringVar(value="10")
        self.critical_hour_end_var = tk.StringVar(value="18")
        self.alpha_result_var = tk.StringVar(value="—")
        self.overhang_depth_var = tk.StringVar(value="—")
        self.highlight_critical_var = tk.BooleanVar(value=True)

        loc = ttk.LabelFrame(form_frame, text="Ubicación", padding=8)
        loc.pack(fill=tk.X, pady=(0, 8))
        for label, var in [
            ("Nombre del sitio", self.site_name_var),
            ("Latitud (Sur = −)", self.lat_var),
            ("Longitud (Oeste = −)", self.lon_var),
        ]:
            row = ttk.Frame(loc)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=label, width=22).pack(side=tk.LEFT)
            ttk.Entry(row, textvariable=var, width=12).pack(side=tk.LEFT, fill=tk.X, expand=True)

        measures = ttk.LabelFrame(form_frame, text="Medidas en corte (m)", padding=8)
        measures.pack(fill=tk.X, pady=(0, 8))
        for label, var in [
            ("Antepecho (piso → ventana)", self.sill_height_var),
            ("Altura ventana", self.window_height_var),
            ("Vano (cierre ventana → alero)", self.gap_to_overhang_var),
        ]:
            row = ttk.Frame(measures)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=label, width=22).pack(side=tk.LEFT)
            ttk.Entry(row, textvariable=var, width=12).pack(side=tk.LEFT)

        results = ttk.LabelFrame(form_frame, text="Resultado del alero", padding=8)
        results.pack(fill=tk.X, pady=(0, 8))
        for label, var in [
            ("Ángulo α (°)", self.alpha_result_var),
            ("Profundidad P (m)", self.overhang_depth_var),
        ]:
            row = ttk.Frame(results)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=label, width=22).pack(side=tk.LEFT)
            ttk.Label(row, textvariable=var, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        ttk.Label(
            results,
            text="P = (h_v + h_g) / tan(α)  |  α = altitud al mediodía solar (mes más bajo)",
            font=("Segoe UI", 8),
            wraplength=300,
        ).pack(anchor=tk.W, pady=(4, 0))

        crit = ttk.LabelFrame(form_frame, text="Período crítico (protección verano)", padding=8)
        crit.pack(fill=tk.X, pady=(0, 8))
        months_row = ttk.Frame(crit)
        months_row.pack(fill=tk.X)
        for idx, month in enumerate(range(1, 13)):
            var = tk.BooleanVar(value=month in DEFAULT_CRITICAL_MONTHS)
            self._month_vars[month] = var
            ttk.Checkbutton(
                months_row,
                text=MONTH_NAMES[month],
                variable=var,
                width=4,
            ).grid(row=idx // 6, column=idx % 6, sticky=tk.W)
        row_ch = ttk.Frame(crit)
        row_ch.pack(fill=tk.X, pady=(6, 2))
        ttk.Label(row_ch, text="Horas críticas", width=22).pack(side=tk.LEFT)
        ttk.Entry(row_ch, textvariable=self.critical_hour_start_var, width=4).pack(side=tk.LEFT)
        ttk.Label(row_ch, text=" a ").pack(side=tk.LEFT)
        ttk.Entry(row_ch, textvariable=self.critical_hour_end_var, width=4).pack(side=tk.LEFT)
        ttk.Checkbutton(
            crit,
            text="Resaltar período crítico en carta",
            variable=self.highlight_critical_var,
        ).pack(anchor=tk.W, pady=(4, 0))

        ttk.Button(form_frame, text="Calcular alero", command=self.calculate_overhang).pack(
            fill=tk.X, pady=(0, 6)
        )

        self.report_text = tk.Text(form_frame, height=6, width=38, wrap=tk.WORD, font=("Segoe UI", 8))
        self.report_text.pack(fill=tk.X, pady=(0, 8))
        self.report_text.configure(state=tk.DISABLED)

        chart = ttk.LabelFrame(form_frame, text="Carta", padding=8)
        chart.pack(fill=tk.X, pady=(0, 8))
        for label, var in [
            ("Hora inicio (líneas)", self.hour_start_var),
            ("Hora fin (líneas)", self.hour_end_var),
        ]:
            row = ttk.Frame(chart)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(row, text=label, width=22).pack(side=tk.LEFT)
            ttk.Entry(row, textvariable=var, width=12).pack(side=tk.LEFT)

        ttk.Button(form_frame, text="Actualizar carta", command=self.update_chart).pack(
            fill=tk.X, pady=(0, 6)
        )

        save_frame = ttk.Frame(form_frame)
        save_frame.pack(fill=tk.X, pady=(0, 8))
        ttk.Button(
            save_frame,
            text="PNG",
            command=lambda: self.save(export_png=True, export_pdf=False),
        ).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(
            save_frame,
            text="PDF",
            command=lambda: self.save(export_png=False, export_pdf=True),
        ).pack(side=tk.LEFT, padx=(0, 4))
        ttk.Button(save_frame, text="Guardar como…", command=self.save_as).pack(side=tk.LEFT)

        row_out = ttk.Frame(form_frame)
        row_out.pack(fill=tk.X, pady=2)
        ttk.Entry(row_out, textvariable=self.output_dir_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Button(row_out, text="…", width=3, command=self._browse_output_dir).pack(side=tk.LEFT)

        self.show_matplotlib_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            form_frame,
            text="Ventana matplotlib al guardar",
            variable=self.show_matplotlib_var,
        ).pack(anchor=tk.W)

        self._build_authorship_block(form_frame)

        self.after(100, self.calculate_overhang)

    def _build_authorship_block(self, parent: ttk.Frame) -> None:
        credit = ttk.LabelFrame(parent, text="Autoría", padding=8)
        credit.pack(fill=tk.X, pady=(8, 0))

        ttk.Label(
            credit,
            text=AUTHORS,
            font=("Segoe UI", 8),
            wraplength=300,
        ).pack(anchor=tk.W)
        ttk.Label(
            credit,
            text=INSTITUTION,
            font=("Segoe UI", 8, "bold"),
        ).pack(anchor=tk.W, pady=(2, 4))

        logos = available_logos()
        if logos:
            row = ttk.Frame(credit)
            row.pack(anchor=tk.W)
            self._logo_refs: list[tk.PhotoImage] = []
            for logo_path in logos:
                try:
                    img = tk.PhotoImage(file=str(logo_path))
                    self._logo_refs.append(img)
                    ttk.Label(row, image=img).pack(side=tk.LEFT, padx=(0, 8))
                except tk.TclError:
                    pass

    def _build_preview_panel(self) -> None:
        self.preview_frame = ttk.LabelFrame(self, text="Vista previa", padding=8)
        self.preview_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10), pady=10)

    def _build_status_bar(self) -> None:
        status_frame = ttk.Frame(self)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=(0, 10))
        self.status_var = tk.StringVar(value="Listo")
        ttk.Label(status_frame, textvariable=self.status_var).pack(side=tk.LEFT)
        ttk.Label(
            status_frame,
            text=CREDIT_LINE,
            font=("Segoe UI", 7),
            foreground="#555555",
        ).pack(side=tk.RIGHT)

    def _bind_shortcuts(self) -> None:
        self.bind("<F5>", lambda _event: self.update_chart())

    def _browse_output_dir(self) -> None:
        selected = filedialog.askdirectory(title="Seleccionar carpeta de salida")
        if selected:
            self.output_dir_var.set(selected)

    def _selected_months(self) -> frozenset[int]:
        return frozenset(m for m, var in self._month_vars.items() if var.get())

    def _parse_config(self) -> CartaSolarConfig:
        return CartaSolarConfig(
            site_name=self.site_name_var.get().strip(),
            lat=float(self.lat_var.get().strip().replace(",", ".")),
            lon=float(self.lon_var.get().strip().replace(",", ".")),
            hour_start=int(self.hour_start_var.get().strip()),
            hour_end=int(self.hour_end_var.get().strip()),
            output_dir=Path(self.output_dir_var.get().strip()),
            sill_height_m=float(self.sill_height_var.get().strip().replace(",", ".")),
            window_height_m=float(self.window_height_var.get().strip().replace(",", ".")),
            gap_to_overhang_m=float(self.gap_to_overhang_var.get().strip().replace(",", ".")),
            critical_months=self._selected_months(),
            critical_hour_start=int(self.critical_hour_start_var.get().strip()),
            critical_hour_end=int(self.critical_hour_end_var.get().strip()),
            highlight_critical_period=self.highlight_critical_var.get(),
        )

    def _resolve_config_with_alpha(self) -> CartaSolarConfig:
        return apply_computed_mask(self._parse_config())

    def _update_result_labels(self, config: CartaSolarConfig) -> None:
        if config.mask_alt is None:
            self.alpha_result_var.set("—")
            self.overhang_depth_var.set("—")
            return
        depth = overhang_projection(config.effective_shading_height_m, config.mask_alt)
        self.alpha_result_var.set(f"{config.mask_alt:.1f}")
        self.overhang_depth_var.set(f"{depth:.3f}")

    def _update_report(self, config: CartaSolarConfig) -> None:
        samples = collect_critical_samples(
            config.lat,
            config.critical_months,
            config.critical_hour_start,
            config.critical_hour_end,
        )
        noon_month: int | None = None
        if config.mask_alt is not None:
            _, noon_month = compute_noon_alpha(config.lat, config.critical_months)
        text = format_exposure_report(
            samples, config.mask_alt, noon_month=noon_month
        )
        self.report_text.configure(state=tk.NORMAL)
        self.report_text.delete("1.0", tk.END)
        self.report_text.insert(tk.END, text)
        self.report_text.configure(state=tk.DISABLED)

    def _render_figure(self, figure: plt.Figure) -> None:
        if self._canvas is not None:
            self._canvas.get_tk_widget().destroy()
        if self._toolbar is not None:
            self._toolbar.destroy()

        self._figure = figure
        self._canvas = FigureCanvasTkAgg(figure, master=self.preview_frame)
        self._canvas.draw()
        self._canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        self._toolbar = NavigationToolbar2Tk(self._canvas, self.preview_frame)
        self._toolbar.update()
        self._toolbar.pack(fill=tk.X)

    def calculate_overhang(self) -> None:
        try:
            config = self._resolve_config_with_alpha()
            self._update_result_labels(config)
            figure = generate_carta_solar(config)
            self._render_figure(figure)
            self._update_report(config)
            p = overhang_projection(config.effective_shading_height_m, config.mask_alt)
            self.status_var.set(
                f"α = {config.mask_alt:.1f}°  P = {p:.3f} m — {config.site_name}"
            )
        except ValueError as exc:
            self.status_var.set("Error de validación")
            messagebox.showerror("Datos inválidos", str(exc))
        except Exception as exc:
            self.status_var.set("Error al calcular alero")
            messagebox.showerror("Error", f"No se pudo calcular el alero:\n{exc}")

    def update_chart(self) -> None:
        self.calculate_overhang()

    def _ensure_figure(self) -> tuple[CartaSolarConfig, plt.Figure]:
        config = self._resolve_config_with_alpha()
        figure = generate_carta_solar(config)
        self._render_figure(figure)
        return config, figure

    def save(self, *, export_png: bool, export_pdf: bool) -> None:
        try:
            config, figure = self._ensure_figure()
            saved = save_carta_solar(figure, config, png=export_png, pdf=export_pdf)
            paths_text = "\n".join(str(path) for path in saved.values())
            self.status_var.set(f"Guardado — {config.site_name}")
            messagebox.showinfo("Guardado", f"Archivos generados:\n{paths_text}")
            self._maybe_show_matplotlib(figure)
        except ValueError as exc:
            messagebox.showerror("Datos inválidos", str(exc))
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo guardar la carta solar:\n{exc}")

    def save_as(self) -> None:
        try:
            config, figure = self._ensure_figure()
            default_name = build_output_basename(config)
            selected = filedialog.asksaveasfilename(
                title="Guardar carta solar",
                initialdir=str(config.output_dir),
                initialfile=default_name,
                defaultextension=".png",
                filetypes=[("PNG", "*.png"), ("PDF", "*.pdf")],
            )
            if not selected:
                return
            path = save_carta_solar_to_path(figure, Path(selected), dpi=config.dpi)
            self.status_var.set(f"Guardado — {path.name}")
            messagebox.showinfo("Guardado", f"Archivo generado:\n{path}")
            self._maybe_show_matplotlib(figure)
        except ValueError as exc:
            messagebox.showerror("Datos inválidos", str(exc))
        except Exception as exc:
            messagebox.showerror("Error", f"No se pudo guardar la carta solar:\n{exc}")

    def _maybe_show_matplotlib(self, figure: plt.Figure) -> None:
        if self.show_matplotlib_var.get():
            plt.figure(figure.number)
            plt.show()


def main() -> None:
    app = CartaSolarApp()
    app.mainloop()


if __name__ == "__main__":
    main()
