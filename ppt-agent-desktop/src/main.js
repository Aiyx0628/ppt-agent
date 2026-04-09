const { app, BrowserWindow } = require("electron");

function createWindow() {
  const window = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 960,
    minHeight: 640,
    title: "ppt-agent-desktop",
  });

  window.loadURL(
    "data:text/html;charset=UTF-8," +
      encodeURIComponent(`
        <!doctype html>
        <html>
          <head>
            <meta charset="utf-8" />
            <title>ppt-agent-desktop</title>
            <style>
              body {
                margin: 0;
                min-height: 100vh;
                display: grid;
                place-items: center;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
                background: linear-gradient(135deg, #f7f5ef, #dce8f8);
                color: #162033;
              }
              main {
                padding: 32px 40px;
                border-radius: 24px;
                background: rgba(255, 255, 255, 0.75);
                box-shadow: 0 24px 60px rgba(22, 32, 51, 0.14);
                text-align: center;
              }
              h1 {
                margin: 0 0 12px;
                font-size: 32px;
              }
              p {
                margin: 0;
                font-size: 16px;
              }
            </style>
          </head>
          <body>
            <main>
              <h1>ppt-agent-desktop</h1>
              <p>Electron shell initialized.</p>
            </main>
          </body>
        </html>
      `)
  );
}

app.whenReady().then(() => {
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
