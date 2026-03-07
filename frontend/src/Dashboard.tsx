import { useState, useEffect } from 'react'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js'
import { Bar, Line } from 'react-chartjs-2'

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
)

const STORAGE_KEY = 'api_key'

interface ScoreBucket {
  bucket: string
  count: number
}

interface ScoresResponse {
  lab_id: number
  buckets: ScoreBucket[]
}

interface TimelineEntry {
  date: string
  submissions: number
}

interface TimelineResponse {
  lab_id: number
  timeline: TimelineEntry[]
}

interface PassRateEntry {
  task_name: string
  passed: number
  failed: number
  pass_rate: number
}

interface PassRatesResponse {
  lab_id: number
  pass_rates: PassRateEntry[]
}

interface Lab {
  id: number
  name: string
}

type DashboardState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; scores: ScoresResponse; timeline: TimelineResponse; passRates: PassRatesResponse }
  | { status: 'error'; message: string }

export default function Dashboard() {
  const [token, setToken] = useState(() => localStorage.getItem(STORAGE_KEY) ?? '')
  const [labs, setLabs] = useState<Lab[]>([])
  const [selectedLab, setSelectedLab] = useState<number | null>(null)
  const [state, setState] = useState<DashboardState>({ status: 'idle' })

  useEffect(() => {
    if (!token) return

    fetch('/labs/', {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`)
        return res.json()
      })
      .then((data: Lab[]) => {
        setLabs(data)
        if (data.length > 0) {
          setSelectedLab(data[0].id)
        }
      })
      .catch((err: Error) => {
        console.error('Failed to fetch labs:', err)
      })
  }, [token])

  useEffect(() => {
    if (!token || selectedLab === null) return

    setState({ status: 'loading' })

    const fetchWithAuth = async <T,>(url: string): Promise<T> => {
      const res = await fetch(url, {
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      return (await res.json()) as T
    }

    Promise.all([
      fetchWithAuth<ScoresResponse>(`/analytics/scores?lab=${selectedLab}`),
      fetchWithAuth<TimelineResponse>(`/analytics/timeline?lab=${selectedLab}`),
      fetchWithAuth<PassRatesResponse>(`/analytics/pass-rates?lab=${selectedLab}`),
    ])
      .then(([scores, timeline, passRates]) => {
        setState({
          status: 'success',
          scores,
          timeline,
          passRates,
        })
      })
      .catch((err: Error) => {
        setState({ status: 'error', message: err.message })
      })
  }, [token, selectedLab])

  if (!token) {
    return (
      <div className="dashboard">
        <h1>Dashboard</h1>
        <p>Please connect with your API key to view analytics.</p>
      </div>
    )
  }

  const handleLabChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedLab(Number(e.target.value))
  }

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <h1>Analytics Dashboard</h1>
        <div className="lab-selector">
          <label htmlFor="lab-select">Select Lab: </label>
          <select
            id="lab-select"
            value={selectedLab ?? ''}
            onChange={handleLabChange}
            disabled={labs.length === 0}
          >
            {labs.map((lab) => (
              <option key={lab.id} value={lab.id}>
                {lab.name} (ID: {lab.id})
              </option>
            ))}
          </select>
        </div>
      </header>

      {state.status === 'loading' && <p className="loading">Loading analytics...</p>}

      {state.status === 'error' && (
        <p className="error">Error: {state.message}</p>
      )}

      {state.status === 'success' && (
        <>
          <section className="chart-section">
            <h2>Score Distribution</h2>
            <div className="chart-container">
              <Bar
                data={{
                  labels: state.scores.buckets.map((b) => b.bucket),
                  datasets: [
                    {
                      label: 'Submissions',
                      data: state.scores.buckets.map((b) => b.count),
                      backgroundColor: 'rgba(54, 162, 235, 0.6)',
                      borderColor: 'rgba(54, 162, 235, 1)',
                      borderWidth: 1,
                    },
                  ],
                }}
                options={{
                  responsive: true,
                  plugins: {
                    legend: { display: false },
                    title: {
                      display: true,
                      text: 'Submissions per Score Bucket',
                    },
                  },
                  scales: {
                    y: {
                      beginAtZero: true,
                      ticks: { stepSize: 1 },
                    },
                  },
                }}
              />
            </div>
          </section>

          <section className="chart-section">
            <h2>Submission Timeline</h2>
            <div className="chart-container">
              <Line
                data={{
                  labels: state.timeline.timeline.map((t) => t.date),
                  datasets: [
                    {
                      label: 'Submissions',
                      data: state.timeline.timeline.map((t) => t.submissions),
                      borderColor: 'rgba(75, 192, 192, 1)',
                      backgroundColor: 'rgba(75, 192, 192, 0.2)',
                      tension: 0.3,
                    },
                  ],
                }}
                options={{
                  responsive: true,
                  plugins: {
                    legend: { display: false },
                    title: {
                      display: true,
                      text: 'Submissions per Day',
                    },
                  },
                  scales: {
                    y: {
                      beginAtZero: true,
                      ticks: { stepSize: 1 },
                    },
                  },
                }}
              />
            </div>
          </section>

          <section className="table-section">
            <h2>Pass Rates per Task</h2>
            <table>
              <thead>
                <tr>
                  <th>Task Name</th>
                  <th>Passed</th>
                  <th>Failed</th>
                  <th>Pass Rate</th>
                </tr>
              </thead>
              <tbody>
                {state.passRates.pass_rates.map((entry, index) => (
                  <tr key={index}>
                    <td>{entry.task_name}</td>
                    <td>{entry.passed}</td>
                    <td>{entry.failed}</td>
                    <td>{(entry.pass_rate * 100).toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>
        </>
      )}
    </div>
  )
}
