import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import io

# ---------------------------------------------------------
# CONFIGURAÇÃO DE TELA E TEMA VISUAL ESCURO CUSTOMIZADO
# ---------------------------------------------------------
st.set_page_config(page_title="Extrapolação Hidrodinâmica", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #0e131f; color: #f0f4fc; }
    section[data-testid="stSidebar"] { background-color: #141b2d; border-right: 1px solid #222d45; }
    h1, h2, h3, h4, p, label { color: #f0f4fc !important; font-family: 'Segoe UI', sans-serif; }
    .streamlit-expanderHeader { background-color: #182238 !important; border-radius: 6px !important; color: #58a6ff !important; border: 1px solid #283757; }
    div[data-baseweb="input"] { background-color: #1b263b; border-color: #283757; color: #ffffff; }
    .stAlert { border-radius: 8px; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #141b2d; border-radius: 4px 4px 0 0; padding-top: 10px; padding-bottom: 10px; }
    .stTabs [aria-selected="true"] { background-color: #182238 !important; border-bottom: 2px solid #58a6ff; }
</style>
""", unsafe_allow_html=True)

st.title("Extrapolação Modelo-Protótipo")
st.markdown("##### Análise Universal por Froude e Hughes • Engenharia Naval")

# ---------------------------------------------------------
# BARRA LATERAL: PARÂMETROS
# ---------------------------------------------------------
st.sidebar.header("Parâmetros do Modelo")
Lm = st.sidebar.number_input("Comprimento do Modelo Lm (m)", value=1.42, format="%.4f")
Sm = st.sidebar.number_input("Área Molhada Sm (m²)", value=0.2949, format="%.4f")
lamb = st.sidebar.slider("Fator de Escala (λ)", min_value=10.0, max_value=250.0, value=100.0, step=1.0)
k_factor = st.sidebar.number_input("Fator de Forma (1+k)", value=1.10)

st.sidebar.header("Propriedades dos Fluidos")
rho_m = st.sidebar.number_input("Massa Específica Água Doce (kg/m³)", value=1000.0)
nu_m = st.sidebar.number_input("Visc. Cinemática Água Doce (m²/s)", value=1.14e-6, format="%e")
rho_s = st.sidebar.number_input("Massa Específica Água Salgada (kg/m³)", value=1025.0)
nu_s = st.sidebar.number_input("Visc. Cinemática Água Salgada (m²/s)", value=1.19e-6, format="%e")
g = 9.81

# ---------------------------------------------------------
# CARREGAMENTO DOS DADOS EXPERIMENTAIS
# ---------------------------------------------------------
st.header("Importação de Dados do Tanque de Provas")
st.info("Envie a folha de cálculo Excel (.xlsx) ou .csv. A Coluna 1 deve conter a Velocidade (m/s) e a Coluna 2 a Resistência Medida (N).")

uploaded_file = st.file_uploader("Selecione o ficheiro", type=["csv", "xlsx"])

if uploaded_file is not None:
    try:
        # Leitura bruta do arquivo
        if uploaded_file.name.endswith('.csv'):
            df_input = pd.read_csv(uploaded_file)
        else:
            df_input = pd.read_excel(uploaded_file)
        
        # FILTRO INTELIGENTE DE LIMPEZA DE DADOS (Data Cleaning)
        df_input = df_input.dropna(axis=1, how='all')
        df_input = df_input.dropna(axis=0, how='all')
        
        vm_col = df_input.columns[0]
        rtm_col = df_input.columns[1]
        
        df = pd.DataFrame()
        df['Vm (m/s)'] = pd.to_numeric(df_input[vm_col], errors='coerce')
        df['RTm (N)'] = pd.to_numeric(df_input[rtm_col], errors='coerce')
        
        df = df.dropna().reset_index(drop=True)
        
        # Cálculos de Hidrodinâmica
        df['Fn'] = df['Vm (m/s)'] / np.sqrt(g * Lm)
        df['Vs (m/s)'] = df['Vm (m/s)'] * np.sqrt(lamb)
        df['Rem'] = (df['Vm (m/s)'] * Lm) / nu_m
        df['Res'] = (df['Vs (m/s)'] * Lm * lamb) / nu_s

        df['CTm'] = df['RTm (N)'] / (0.5 * rho_m * Sm * df['Vm (m/s)']**2)
        df['CFm'] = 0.075 / (np.log10(df['Rem']) - 2)**2
        df['CFs'] = 0.075 / (np.log10(df['Res']) - 2)**2

        # Método de Froude
        df['CRm'] = df['CTm'] - df['CFm']
        df['CTs_Froude'] = df['CFs'] + df['CRm']
        df['RTs_Froude (kN)'] = (df['CTs_Froude'] * 0.5 * rho_s * (Sm * lamb**2) * df['Vs (m/s)']**2) / 1000
        df['PE_Froude (kW)'] = df['RTs_Froude (kN)'] * df['Vs (m/s)']

        # Método de Hughes
        df['CVm'] = k_factor * df['CFm']
        df['CWm'] = df['CTm'] - df['CVm']
        df['CVs'] = k_factor * df['CFs']
        df['CTs_Hughes'] = df['CVs'] + df['CWm']
        df['RTs_Hughes (kN)'] = (df['CTs_Hughes'] * 0.5 * rho_s * (Sm * lamb**2) * df['Vs (m/s)']**2) / 1000
        df['PE_Hughes (kW)'] = df['RTs_Hughes (kN)'] * df['Vs (m/s)']

        # Sistema de Alerta Invisível (Reynolds Crítico)
        if df['Rem'].iloc[0] < 500000:
            st.warning("⚠️ **Aviso de Física Hidrodinâmica:** O modelo foi rebocado em velocidade excessivamente baixa na fase inicial (Reynolds Crítico < 5E5). O escoamento pode não ser totalmente turbulento, podendo gerar distorções pontuais de escala nesta faixa.")
        else:
            st.success("Dados carregados e extrapolados com sucesso!")

        # ---------------------------------------------------------
        # SISTEMA DE ABAS (DASHBOARD)
        # ---------------------------------------------------------
        tab1, tab2 = st.tabs(["📊 Dados e Matrizes", "📈 Curvas Visuais"])

        with tab1:
            st.markdown("### Matriz de Resultados da Extrapolação")
            colunas_exibicao = [
                'Vm (m/s)', 'RTm (N)', 'Fn', 'Vs (m/s)', 
                'RTs_Froude (kN)', 'PE_Froude (kW)',
                'RTs_Hughes (kN)', 'PE_Hughes (kW)'
            ]
            st.dataframe(df[colunas_exibicao].style.format("{:.3f}"))

            csv_export = df[colunas_exibicao].to_csv(index=False, sep=';', decimal=',').encode('utf-8-sig')
            st.download_button(label="📥 Baixar Resultados em Excel", data=csv_export, file_name="extrapolacao_resultados.csv", mime="text/csv")
            
            st.divider()

            st.markdown("### Calculadora Preditiva de Projeto")
            st.info("💡 **Ferramenta Preditiva:** Deseja estimar a potência para uma velocidade comercial específica do navio real? Digite a velocidade desejada abaixo (em nós) e o sistema realizará a interpolação matemática avançada sobre a curva.")
            
            vel_nos = st.number_input("Velocidade do Protótipo (Nós):", min_value=1.0, max_value=100.0, value=15.0, step=0.5)
            vel_ms = vel_nos * 0.514444
            
            if vel_ms >= df['Vs (m/s)'].min() and vel_ms <= df['Vs (m/s)'].max():
                pe_f_interp = np.interp(vel_ms, df['Vs (m/s)'], df['PE_Froude (kW)'])
                pe_h_interp = np.interp(vel_ms, df['Vs (m/s)'], df['PE_Hughes (kW)'])
                st.success(f"Para navegar a **{vel_nos:.1f} nós** ({vel_ms:.2f} m/s), o navio exigirá aproximadamente **{pe_f_interp:.0f} kW** (Froude) ou **{pe_h_interp:.0f} kW** (Hughes).")
            else:
                st.error("A velocidade solicitada está fora do intervalo extrapolado do ensaio físico. Tente um valor dentro da faixa de dados.")

            st.divider()

            with st.expander("🔽 Clique para abrir a Memória Analítica de Cálculo (Passo a Passo)", expanded=False):
                st.markdown("### Demonstração Analítica")
                vel_escolhida = st.selectbox("Selecione a velocidade (Vm) para visualizar as fórmulas substituídas:", df['Vm (m/s)'].unique())
                row = df[df['Vm (m/s)'] == vel_escolhida].iloc[0]
                
                col_esq, col_dir = st.columns(2)
                with col_esq:
                    st.markdown("#### Cálculos Preliminares")
                    st.latex(rf"L_s = L_m \times \lambda = {Lm} \times {lamb} = {Lm * lamb:.2f} \text{{ m}}")
                    st.latex(rf"S_s = S_m \times \lambda^2 = {Sm} \times {lamb**2} = {Sm * lamb**2:.4f} \text{{ m}}^2")
                    st.latex(rf"V_s = V_m \times \sqrt{{\lambda}} = {row['Vm (m/s)']} \times \sqrt{{{lamb}}} = {row['Vs (m/s)']:.4f} \text{{ m/s}}")
                    st.latex(rf"Re_m = \frac{{V_m \cdot L_m}}{{\nu_m}} = {row['Rem']:.2e}")
                    st.latex(rf"Re_s = \frac{{V_s \cdot L_s}}{{\nu_s}} = {row['Res']:.2e}")

                with col_dir:
                    st.markdown("#### Autoria: Método de Froude")
                    st.latex(rf"C_{{Tm}} = \frac{{R_{{Tm}}}}{{\frac{{1}}{{2}} \rho_m S_m V_m^2}} = {row['CTm']:.3e}")
                    st.latex(rf"C_{{Fm}} = \frac{{0,075}}{{(\log_{{10}} Re_m - 2)^2}} = {row['CFm']:.3e}")
                    st.latex(rf"C_{{Rm}} = C_{{Tm}} - C_{{Fm}} = {row['CRm']:.3e}")
                    st.latex(rf"C_{{Fs}} = \frac{{0,075}}{{(\log_{{10}} Re_s - 2)^2}} = {row['CFs']:.3e}")
                    st.latex(rf"C_{{Ts}} = C_{{Fs}} + C_{{Rm}} = {row['CTs_Froude']:.3e}")
                    st.latex(rf"P_{{E(Froude)}} = R_{{Ts}} \times V_s = \mathbf{{{row['PE_Froude (kW)']:.2f} \text{{ kW}}}}")
                    
                    st.markdown("#### Autoria: Método de Hughes")
                    st.latex(rf"C_{{Vm}} = (1+k)C_{{Fm}} = {row['CVm']:.3e}")
                    st.latex(rf"C_{{Wm}} = C_{{Tm}} - C_{{Vm}} = {row['CWm']:.3e}")
                    st.latex(rf"C_{{Vs}} = (1+k)C_{{Fs}} = {row['CVs']:.3e}")
                    st.latex(rf"C_{{Ts}} = C_{{Vs}} + C_{{Wm}} = {row['CTs_Hughes']:.3e}")
                    st.latex(rf"P_{{E(Hughes)}} = R_{{Ts}} \times V_s = \mathbf{{{row['PE_Hughes (kW)']:.2f} \text{{ kW}}}}")

        with tab2:
            st.markdown("### Curvas de Desempenho do Protótipo")
            st.info("Utilize os botões abaixo de cada gráfico para descarregar a imagem compatível com relatórios (PNG com fundo branco).")
            
            col1, col2 = st.columns(2)

            with col1:
                fig1, ax1 = plt.subplots()
                ax1.plot(df['Fn'], df['PE_Froude (kW)'], marker='o', label='Método de Froude', color='#1f77b4')
                ax1.plot(df['Fn'], df['PE_Hughes (kW)'], marker='o', label='Método de Hughes', color='#ff7f0e')
                ax1.set_xlabel('Número de Froude (Fn)')
                ax1.set_ylabel('Potência Efetiva (kW)')
                ax1.set_title('Potência vs. Número de Froude')
                ax1.legend()
                ax1.grid(True, linestyle='--', alpha=0.7)
                st.pyplot(fig1)
                
                buf1 = io.BytesIO()
                fig1.savefig(buf1, format="png", bbox_inches="tight")
                st.download_button(label="🖼️ Baixar Gráfico de Potência (PNG)", data=buf1.getvalue(), file_name="grafico_potencia.png", mime="image/png")

            with col2:
                fig2, ax2 = plt.subplots()
                ax2.plot(df['Fn'], df['RTs_Froude (kN)'], marker='s', label='Método de Froude', color='#1f77b4')
                ax2.plot(df['Fn'], df['RTs_Hughes (kN)'], marker='s', label='Método de Hughes', color='#ff7f0e')
                ax2.set_xlabel('Número de Froude (Fn)')
                ax2.set_ylabel('Resistência Total (kN)')
                ax2.set_title('Resistência vs. Número de Froude')
                ax2.legend()
                ax2.grid(True, linestyle='--', alpha=0.7)
                st.pyplot(fig2)
                
                buf2 = io.BytesIO()
                fig2.savefig(buf2, format="png", bbox_inches="tight")
                st.download_button(label="🖼️ Baixar Gráfico de Resistência (PNG)", data=buf2.getvalue(), file_name="grafico_resistencia.png", mime="image/png")

    except Exception as e:
        st.error(f"Ocorreu um erro ao processar o ficheiro. Certifique-se de que a planilha contém números. Detalhe técnico: {e}")
else:
    st.warning("Aguardando carregamento de planilha para execução dos cálculos...")