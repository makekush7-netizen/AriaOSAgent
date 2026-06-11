#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .setup(|app| {
      if cfg!(debug_assertions) {
        app.handle().plugin(
          tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build(),
        )?;
      }
      Ok(())
    })
    .on_window_event(|window, event| {
      if let tauri::WindowEvent::CloseRequested { api, .. } = event {
        if window.label() == "main" {
          // Only close this window, keep the widget alive
          window.hide().unwrap_or(());
          api.prevent_close();
        }
        // Widget closing normally will cause app to exit (last window gone)
      }
    })
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}

