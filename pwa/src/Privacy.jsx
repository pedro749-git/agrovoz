import { useNavigate } from 'react-router-dom'
import AppBar from './AppBar.jsx'

// Static RGPD privacy notice, reachable logged-out (linked from the login
// screen's consent line) and logged-in. Deliberately honest about being a
// prototype: it names the real processors (Supabase, Alibaba Cloud) and warns
// against entering real third-party personal data. Content is user-facing ->
// Spanish. Update `CONTACT_EMAIL` if the project changes hands.
const CONTACT_EMAIL = 'pedroaccflores@gmail.com'

// One titled block per RGPD topic, so the notice reads as short scannable
// sections instead of a legal wall of text.
function Section({ title, children }) {
  return (
    <section className="mt-5">
      <h2 className="text-sm font-bold text-soil">{title}</h2>
      <div className="mt-1.5 space-y-2 text-sm leading-relaxed text-ink">{children}</div>
    </section>
  )
}

function Privacy() {
  const navigate = useNavigate()

  return (
    <div className="flex min-h-dvh flex-col bg-bone text-soil">
      <AppBar title="Política de privacidad" onBack={() => navigate('/')} />

      <main className="mx-auto w-full max-w-md flex-1 px-5 pb-safe pt-4">
        {/* Prototype warning first: it frames everything below. */}
        <div className="rounded-xl border border-line bg-card p-4 text-sm leading-relaxed text-ink shadow-card">
          <p className="font-semibold text-soil">AgroVoz es un prototipo de demostración</p>
          <p className="mt-1">
            Forma parte de un Trabajo de Fin de Grado y de un hackathon. Las
            cuentas de prueba trabajan con datos ficticios: por favor,{' '}
            <span className="font-semibold">
              no introduzcas datos personales reales de terceros
            </span>{' '}
            (nombres, NIF, números ROPO…) en los registros.
          </p>
        </div>

        <Section title="Responsable del tratamiento">
          <p>
            Pedro Flores Navarro, autor del proyecto. Contacto para cualquier
            cuestión sobre tus datos:{' '}
            <a href={`mailto:${CONTACT_EMAIL}`} className="font-semibold text-olive underline">
              {CONTACT_EMAIL}
            </a>
            .
          </p>
        </Section>

        <Section title="Qué datos tratamos">
          <ul className="list-disc space-y-1 pl-5">
            <li>Tu correo electrónico, para crear la cuenta e iniciar sesión.</li>
            <li>
              Los audios de voz que dictas y su transcripción, para generar el
              registro fitosanitario.
            </li>
            <li>
              Los datos que contienen los registros: titular de la explotación,
              NIF, números ROPO y ROMA, parcelas SIGPAC, productos, dosis y
              documentos PDF generados.
            </li>
            <li>
              Si confirmas una ejecución, la fecha del dispositivo y, en su caso,
              las coordenadas de la parcela para consultar la meteorología.
            </li>
          </ul>
        </Section>

        <Section title="Para qué y con qué base legal">
          <p>
            Los datos se usan exclusivamente para elaborar y conservar el
            cuaderno de campo fitosanitario: prestarte el servicio que solicitas
            (art. 6.1.b RGPD) y cumplir la obligación legal de registro y
            conservación que impone el RD 1311/2012 (art. 6.1.c RGPD). No hay
            publicidad, ni analítica, ni cesión a terceros con fines
            comerciales.
          </p>
        </Section>

        <Section title="Dónde se procesan">
          <ul className="list-disc space-y-1 pl-5">
            <li>
              <span className="font-semibold">Supabase</span>: base de datos y
              autenticación de la cuenta.
            </li>
            <li>
              <span className="font-semibold">Alibaba Cloud</span>: almacenamiento
              de audios y PDF (OSS) y procesamiento de voz y texto con modelos
              Qwen (DashScope). Esto puede implicar una transferencia de datos
              fuera del Espacio Económico Europeo.
            </li>
            <li>
              <span className="font-semibold">AEMET / Open-Meteo</span>: solo
              reciben coordenadas y fechas para la consulta meteorológica, nunca
              datos personales.
            </li>
          </ul>
        </Section>

        <Section title="Cuánto tiempo se conservan">
          <p>
            Los registros fitosanitarios se conservan 3 años por obligación
            legal (RD 1311/2012); por eso una corrección o un borrado en la
            aplicación nunca destruye el registro original, solo lo marca como
            sustituido. Los datos de tu cuenta se conservan hasta que solicites
            la baja.
          </p>
        </Section>

        <Section title="Tus derechos">
          <p>
            Puedes ejercer los derechos de acceso, rectificación, supresión,
            oposición, limitación y portabilidad escribiendo al correo de
            contacto. La supresión de registros fitosanitarios está limitada por
            el plazo legal de conservación indicado arriba. También puedes
            reclamar ante la Agencia Española de Protección de Datos (AEPD).
          </p>
        </Section>

        <Section title="Cookies y almacenamiento local">
          <p>
            La aplicación no usa cookies de analítica ni de publicidad. Solo
            guarda en tu dispositivo lo estrictamente necesario para funcionar:
            tu sesión y, si grabas sin conexión, las notas pendientes de
            sincronizar.
          </p>
        </Section>

        <p className="mt-6 pb-6 text-xs text-ink/70">
          Última actualización: 17 de julio de 2026.
        </p>
      </main>
    </div>
  )
}

export default Privacy
