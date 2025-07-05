import { useAuth0 } from '@auth0/auth0-react'
import { useEffect } from 'react'
import axios from 'axios'
import './App.css'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

function App() {
  const { 
    user, 
    isAuthenticated, 
    isLoading, 
    loginWithRedirect, 
    logout, 
    getAccessTokenSilently 
  } = useAuth0()

  // Sync user with backend when authenticated
  useEffect(() => {
    const syncUser = async () => {
      if (isAuthenticated && user) {
        try {
          const token = await getAccessTokenSilently()
          await axios.post(`${API_URL}/api/users/sync`, {
            auth0_id: user.sub,
            email: user.email,
            name: user.name,
            picture: user.picture,
            email_verified: user.email_verified
          }, {
            headers: {
              Authorization: `Bearer ${token}`
            }
          })
        } catch (error) {
          console.error('Failed to sync user:', error)
        }
      }
    }

    syncUser()
  }, [isAuthenticated, user, getAccessTokenSilently])

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="loading-spinner w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full mx-auto mb-4"></div>
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div className="flex items-center">
              <h1 className="text-2xl font-bold text-gray-900">Naptha Course Creator</h1>
            </div>
            <div className="flex items-center space-x-4">
              {isAuthenticated ? (
                <div className="flex items-center space-x-4">
                  <div className="flex items-center space-x-2">
                    <img 
                      src={user.picture} 
                      alt={user.name} 
                      className="w-8 h-8 rounded-full"
                    />
                    <span className="text-gray-700">{user.name}</span>
                  </div>
                  <button
                    onClick={() => logout({ returnTo: window.location.origin })}
                    className="bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 transition-colors"
                  >
                    Logout
                  </button>
                </div>
              ) : (
                <div className="flex items-center space-x-4">
                  <button
                    onClick={() => loginWithRedirect({ screen_hint: 'login' })}
                    className="text-gray-700 hover:text-gray-900 px-4 py-2 rounded-lg hover:bg-gray-100 transition-colors"
                  >
                    Login
                  </button>
                  <button
                    onClick={() => loginWithRedirect({ screen_hint: 'signup' })}
                    className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 transition-colors"
                  >
                    Sign Up
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto py-12 px-4 sm:px-6 lg:px-8">
        {isAuthenticated ? (
          <div className="text-center">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">
              Welcome back, {user.name}!
            </h2>
            <p className="text-xl text-gray-600 mb-8">
              Ready to create amazing courses with AI?
            </p>
            <div className="bg-white rounded-lg shadow-md p-8 max-w-md mx-auto">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Your Profile</h3>
              <div className="space-y-2 text-left">
                <p><strong>Email:</strong> {user.email}</p>
                <p><strong>Status:</strong> {user.email_verified ? 'Verified' : 'Pending verification'}</p>
                <p><strong>Member since:</strong> {new Date(user.updated_at).toLocaleDateString()}</p>
              </div>
            </div>
          </div>
        ) : (
          <div className="text-center">
            <h2 className="text-4xl font-bold text-gray-900 mb-4">
              Welcome to Naptha Course Creator
            </h2>
            <p className="text-xl text-gray-600 mb-8">
              Create engaging courses with AI assistance and human expertise
            </p>
            
            <div className="grid md:grid-cols-3 gap-8 mb-12">
              <div className="bg-white rounded-lg shadow-md p-6">
                <div className="text-blue-600 text-3xl mb-4">🤖</div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">AI-Powered</h3>
                <p className="text-gray-600">Generate course content with advanced AI technology</p>
              </div>
              
              <div className="bg-white rounded-lg shadow-md p-6">
                <div className="text-green-600 text-3xl mb-4">👥</div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Human-in-the-Loop</h3>
                <p className="text-gray-600">DevRel experts review and refine every course</p>
              </div>
              
              <div className="bg-white rounded-lg shadow-md p-6">
                <div className="text-purple-600 text-3xl mb-4">🎯</div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">Targeted Content</h3>
                <p className="text-gray-600">Courses tailored to your specific audience</p>
              </div>
            </div>

            <div className="space-y-4">
              <button
                onClick={() => loginWithRedirect({ screen_hint: 'signup' })}
                className="bg-blue-600 text-white px-8 py-3 rounded-lg hover:bg-blue-700 transition-colors text-lg font-semibold"
              >
                Get Started - Sign Up Free
              </button>
              <div>
                <span className="text-gray-600">Already have an account? </span>
                <button
                  onClick={() => loginWithRedirect({ screen_hint: 'login' })}
                  className="text-blue-600 hover:text-blue-700 font-semibold"
                >
                  Sign In
                </button>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  )
}

export default App 