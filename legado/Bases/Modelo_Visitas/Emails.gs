function enviarConvites() {
  const link = "https://www.appsheet.com/newshortcut/85ad58fd-4fce-4f9b-9b27-084b7894e99c";
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Emails");
  const dados = sheet.getDataRange().getValues(); // A: email, B: nome (opcional)
  const assunto = "Convite - Visitas 61";

  for (let i = 1; i < dados.length; i++) {
    const email = String(dados[i][0] || "").trim();
    const nome  = String(dados[i][4] || "").trim();

    if (!email) continue;

    const corpo = corpoConviteHTML(nome, link);
    MailApp.sendEmail({
      to: email,
      subject: assunto,
      htmlBody: corpo
    });
  }
}


function corpoConviteHTML(nome, link) {
  return `
  <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="background:#f4f6f8;">
    <tr>
      <td align="center" style="padding:32px 12px;">
        <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="620" style="background:#ffffff; border-radius:10px; overflow:hidden;">
          <tr>
            <td style="padding:28px 28px 16px 28px; font-family:Arial, Helvetica, sans-serif;">
              <h1 style="margin:0 0 8px 0; font-size:18px; color:#111111; font-weight:700;">Convite para o aplicativo Visitas 61</h1>
              <p style="margin:0; font-size:14px; color:#444444;">Olá${nome ? ", " + nome : ""},</p>
              <p style="margin:12px 0 0 0; font-size:14px; color:#444444; line-height:1.5;">
                Você está convidado(a) para acessar o <strong>Visitas 61</strong>. Utilize o botão abaixo para entrar:
              </p>
            </td>
          </tr>
          <tr>
            <td align="left" style="padding:8px 28px 16px 28px; font-family:Arial, Helvetica, sans-serif;">
              <!--[if mso]>
              <v:roundrect xmlns:v="urn:schemas-microsoft-com:vml" href="${link}" style="height:44px;v-text-anchor:middle;width:220px;" arcsize="10%" fillcolor="#0b5cab" strokecolor="#0b5cab">
                <w:anchorlock/>
                <center style="color:#ffffff; font-family:Arial, Helvetica, sans-serif; font-size:14px; font-weight:700;">
                  Acessar o Visitas 61
                </center>
              </v:roundrect>
              <![endif]-->
              <!--[if !mso]><!-- -->
              <a href="${link}" style="background-color:#0b5cab; color:#ffffff !important; text-decoration:none; padding:14px 22px; display:inline-block; border-radius:6px; font-weight:600; font-family:Arial, Helvetica, sans-serif;" target="_blank" rel="noopener">
                Acessar o Visitas 61
              </a>
              <!--<![endif]-->
            </td>
          </tr>
          <tr>
            <td style="padding:4px 28px 24px 28px; font-family:Arial, Helvetica, sans-serif;">
              <p style="margin:0; font-size:12px; color:#666666;">
                Se o botão não funcionar, copie e cole este link no navegador:<br>
                <a href="${link}" style="color:#0b5cab; text-decoration:underline;">${link}</a>
              </p>
            </td>
          </tr>
          <tr>
            <td style="padding:16px 28px 28px 28px; font-family:Arial, Helvetica, sans-serif; border-top:1px solid #e9eef3;">
              <p style="margin:0; font-size:12px; color:#666666; line-height:1.5;">
                Atenciosamente,<br>
                Equipe Visitas 61
              </p>
            </td>
          </tr>
        </table>
        <div style="font-family:Arial, Helvetica, sans-serif; font-size:11px; color:#9aa4af; margin-top:12px;">
          Esta é uma mensagem automática. Por favor, não responda.
        </div>
      </td>
    </tr>
  </table>`;
}
