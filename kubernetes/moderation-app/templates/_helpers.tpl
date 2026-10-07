{{- define "monapp.labels" -}}
app.kubernetes.io/name: {{ .Chart.Name }}
{{- end }}